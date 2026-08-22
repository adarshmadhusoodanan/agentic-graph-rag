"""Qdrant vector database client.

Wraps the qdrant-client SDK behind a small interface the rest of the app
depends on, so nothing outside this module needs to know about
PointStruct/VectorParams construction or the difference between the REST
and gRPC transports.
"""

import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def stable_point_id(key: str) -> str:
    """Deterministically derive a valid Qdrant point id from a string key.

    Qdrant point ids must be an unsigned integer or a valid UUID -- an
    arbitrary string like "doc1:chunk3" is rejected outright. Deriving the
    id from a stable key (e.g. "{source_doc_id}:{chunk_index}") means
    re-ingesting the same document updates the same points instead of
    creating duplicates.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


class VectorClient:
    """Thin wrapper around QdrantClient, scoped to one configured collection."""

    def __init__(self) -> None:
        self._client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            grpc_port=settings.QDRANT_GRPC_PORT,
            prefer_grpc=settings.QDRANT_USE_GRPC,
            api_key=(
                settings.QDRANT_API_KEY.get_secret_value()
                if settings.QDRANT_API_KEY
                else None
            ),
        )
        self._collection = settings.QDRANT_COLLECTION_NAME

    def ensure_collection(self) -> None:
        """Create the collection if it doesn't exist yet.

        Safe to call on every startup -- idempotent, so ingestion and the
        API can both call it without coordinating who "owns" collection
        creation.
        """
        if self._client.collection_exists(self._collection):
            logger.info("Qdrant collection '%s' already exists", self._collection)
            return

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(
                size=settings.QDRANT_VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "Created Qdrant collection '%s' (size=%d, distance=cosine)",
            self._collection,
            settings.QDRANT_VECTOR_SIZE,
        )

    def upsert(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        """Insert or update points, one vector + one payload per point.

        ids must be unsigned integers or valid UUID strings (see
        stable_point_id()) -- defaults to fresh random UUIDs if omitted,
        which is fine for one-off inserts but not idempotent re-ingestion.
        """
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]

        points = [
            PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def search(self, query_vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        """Return the top `limit` nearest points as plain dicts (score + payload)."""
        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=limit,
        )
        return [
            {"id": point.id, "score": point.score, "payload": point.payload}
            for point in response.points
        ]

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "VectorClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


@lru_cache
def get_vector_client() -> VectorClient:
    """Return the process-wide VectorClient singleton."""
    return VectorClient()
