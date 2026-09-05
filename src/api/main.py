"""FastAPI app: startup checks + router registration.

Route handlers live in api/routers/, request/response shapes live in
api/schemas.py -- this file's only job is wiring the app together.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routers import health, query
from src.db.neo4j_graph_client import get_neo4j_client
from src.db.qdrant_vector_client import get_vector_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Fail fast at startup, not on the first request.

    Same reasoning as verify_connectivity() elsewhere in this project: a
    misconfigured connection should be an immediate, loud startup failure,
    not a confusing 500 on whatever request happens to hit it first.
    """
    get_neo4j_client().verify_connectivity()
    get_vector_client().ensure_collection()
    logger.info("Startup checks passed: Neo4j and Qdrant are reachable.")
    yield


app = FastAPI(title="Agentic Graph RAG", lifespan=lifespan)
app.include_router(health.router)
app.include_router(query.router)