"""Graph traversal search over extracted entities and relationships.

Query-time counterpart to ingestion/etl.py's entity/relationship
extraction: given an entity name, returns the facts connected to it in
Neo4j -- the "who/what else is connected to this" questions vector search
alone can't answer.
"""

from typing import Any

from src.db.neo4j_graph_client import get_neo4j_client
from src.utils.logger import get_logger

logger = get_logger(__name__)

_NEIGHBORHOOD_QUERY = """
MATCH (e:Entity)
WHERE toLower(e.name) CONTAINS toLower($entity_name)
MATCH (e)-[r]-(neighbor:Entity)
RETURN
    e.name AS entity,
    coalesce(r.label, type(r)) AS relationship,
    neighbor.name AS neighbor,
    neighbor.type AS neighbor_type
LIMIT $limit
"""


def graph_search(entity_name: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return facts connected to entities matching `entity_name`.

    Matches case-insensitively on a substring, not exact equality --
    entities are extracted verbatim by the LLM at ingestion time (see
    ingestion/etl.py's known simplification around entity resolution), so
    a forgiving match here compensates for minor naming variation ("Alice"
    vs "Alice Smith") without requiring the caller to know the exact
    extracted name.

    Relationship direction is intentionally ignored (undirected pattern,
    `-[r]-` not `-[r]->`) -- for "what's connected to X" questions, callers
    generally care about the connection existing, not which node happens
    to be the Cypher source vs target of it.

    One hop only, by design: keeps the query simple and the result set
    bounded. Multi-hop (variable-length path) traversal is a natural
    extension if a question needs it, not included here.
    """
    neo4j = get_neo4j_client()
    records = neo4j.read(_NEIGHBORHOOD_QUERY, entity_name=entity_name, limit=limit)

    return [
        {
            "entity": r["entity"],
            "relationship": r["relationship"],
            "neighbor": r["neighbor"],
            "neighbor_type": r["neighbor_type"],
        }
        for r in records
    ]