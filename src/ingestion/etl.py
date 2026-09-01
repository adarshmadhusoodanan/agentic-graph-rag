"""Document ingestion ETL pipeline.

Turns one raw document into two parallel representations:

  1. Chunks -> embedded (Vertex AI) -> stored in Qdrant, for semantic search.
  2. Entities + relationships -> extracted (Vertex AI) -> stored in Neo4j,
     for graph traversal.

This is the offline half of the architecture described in the README;
src/retrieval reads what this module writes.
"""

from pydantic import BaseModel

from src.db.neo4j_graph_client import get_neo4j_client
from src.db.qdrant_vector_client import get_vector_client, stable_point_id
from src.db.vertex_client import embed_texts, generate_content
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split text into overlapping character-based chunks.

    Overlap keeps context that would otherwise be severed at a chunk
    boundary (e.g. a sentence split across two chunks) available on both
    sides of the split. Character-based rather than token-based: simple,
    dependency-free, and close enough for this project -- swap in a
    tokenizer-aware splitter if chunk size needs to track the embedding
    model's token limit precisely.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Entity / relationship extraction
# ---------------------------------------------------------------------------


class Entity(BaseModel):
    name: str
    type: str  # e.g. PERSON, ORGANIZATION, CONCEPT, PRODUCT


class Relationship(BaseModel):
    source: str
    target: str
    relation: str  # short free-text verb phrase, e.g. "works at"


class ExtractionResult(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]


_EXTRACTION_PROMPT = """Extract the entities and relationships explicitly \
stated in the following text. Do not infer relationships that aren't \
directly supported by the text, and do not invent entities that aren't \
named.

Text:
{text}
"""


def extract_entities_and_relations(
    text: str, max_attempts: int = 2
) -> ExtractionResult:
    """Ask the LLM to extract a small knowledge graph from one chunk of text.

    Retries once on unparseable output before giving up -- occasional schema
    drift from free-form generation is expected, not a hard failure.
    """
    for attempt in range(1, max_attempts + 1):
        response = generate_content(
            _EXTRACTION_PROMPT.format(text=text),
            response_mime_type="application/json",
            response_schema=ExtractionResult,
            temperature=0.0,
        )
        if response.parsed is not None:
            return response.parsed
        logger.warning(
            "Entity extraction returned unparseable output (attempt %d/%d)",
            attempt,
            max_attempts,
        )
    return ExtractionResult(entities=[], relationships=[])


def _normalize_relation_type(relation: str) -> str:
    """Turn a free-text relation phrase into a valid Cypher relationship type.

    Neo4j relationship types can't be parameterized in Cypher -- they must
    be literal identifiers in the query text itself -- so this normalizes
    the LLM's free-text output into a safe [A-Z0-9_]+ token *before* it is
    interpolated into a query string. Never interpolate the raw LLM output
    directly; that would be a genuine Cypher injection risk.
    """
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", relation).strip("_").upper()
    return normalized or "RELATES_TO"


def _write_graph(extraction: ExtractionResult, source_doc_id: str) -> None:
    """MERGE extracted entities/relationships into Neo4j.

    MERGE (not CREATE) so re-ingesting the same document strengthens the
    existing graph instead of duplicating nodes and edges every run.

    Known simplification: entities are merged on exact name match, so
    "Alice" and "Alice Smith" become two separate nodes rather than one --
    entity resolution/deduplication is out of scope for this commit.
    """
    neo4j = get_neo4j_client()

    for entity in extraction.entities:
        neo4j.write(
            "MERGE (e:Entity {name: $name}) SET e.type = $type",
            name=entity.name,
            type=entity.type,
        )

    for rel in extraction.relationships:
        rel_type = _normalize_relation_type(rel.relation)
        neo4j.write(
            f"MERGE (a:Entity {{name: $source}}) "
            f"MERGE (b:Entity {{name: $target}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r.label = $relation, r.source_doc_id = $source_doc_id",
            source=rel.source,
            target=rel.target,
            relation=rel.relation,
            source_doc_id=source_doc_id,
        )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def ingest_document(doc_id: str, text: str) -> None:
    """Ingest one document: chunk -> embed -> Qdrant, and extract -> Neo4j.

    Safe to re-run on the same doc_id -- both sides are idempotent (stable
    point ids in Qdrant via stable_point_id, MERGE in Neo4j).
    """
    chunks = chunk_text(text)
    logger.info("Split document '%s' into %d chunks", doc_id, len(chunks))

    vectors = embed_texts(chunks, task_type="RETRIEVAL_DOCUMENT")
    ids = [stable_point_id(f"{doc_id}:{i}") for i in range(len(chunks))]
    payloads = [
        {"doc_id": doc_id, "chunk_index": i, "text": chunk}
        for i, chunk in enumerate(chunks)
    ]

    vector_client = get_vector_client()
    vector_client.ensure_collection()
    vector_client.upsert(vectors=vectors, payloads=payloads, ids=ids)
    logger.info("Upserted %d vectors for document '%s'", len(chunks), doc_id)

    # One extraction call per chunk -- simplest correct approach for now.
    # Worth batching into fewer, larger calls later if ingestion volume
    # makes per-chunk LLM calls a cost or latency bottleneck.
    for chunk in chunks:
        extraction = extract_entities_and_relations(chunk)
        _write_graph(extraction, source_doc_id=doc_id)
    logger.info("Extracted graph data for document '%s'", doc_id)
