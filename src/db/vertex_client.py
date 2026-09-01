"""Vertex AI (Gemini) client -- embeddings and generation.

Shared by both the ingestion pipeline (embedding documents, extracting
entities/relationships) and query-time retrieval (embedding a search
query), so there's exactly one Vertex AI client in the process and one
place that knows how to call it.
"""

from google import genai
from google.genai import types

from src.config import settings

_client = genai.Client(
    vertexai=True,
    project=settings.GOOGLE_CLOUD_PROJECT,
    location=settings.GOOGLE_CLOUD_REGION,
)


def embed_texts(
    texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[list[float]]:
    """Embed a batch of texts with Vertex AI, truncated to QDRANT_VECTOR_SIZE.

    task_type is asymmetric by design: documents being indexed use
    RETRIEVAL_DOCUMENT (the default here), but a query embedded at search
    time must pass RETRIEVAL_QUERY explicitly -- using the same task_type
    on both sides measurably hurts retrieval quality with this model
    family.
    """
    response = _client.models.embed_content(
        model=settings.EMBEDDING_MODEL_NAME,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=settings.QDRANT_VECTOR_SIZE,
        ),
    )
    return [embedding.values for embedding in response.embeddings]


def generate_content(prompt: str, **config_kwargs):
    """Thin passthrough to Vertex AI's generate_content.

    Kept here so there's still exactly one genai.Client in the process,
    even though most callers (structured extraction, the agent's LLM
    calls) will each pass their own config kwargs.
    """
    return _client.models.generate_content(
        model=settings.LLM_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )