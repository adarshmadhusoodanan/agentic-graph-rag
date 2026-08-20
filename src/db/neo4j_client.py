"""Neo4j graph database client.

Wraps the official neo4j driver behind a small interface the rest of the
app depends on, so nothing outside this module needs to know about
driver.execute_query(), session lifecycles, or transaction functions.
"""

from functools import lru_cache
from typing import Any

from neo4j import Driver, GraphDatabase, RoutingControl
from neo4j.exceptions import ServiceUnavailable

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Neo4jClient:
    """Thin wrapper around a Neo4j Driver, scoped to one configured database."""

    def __init__(self) -> None:
        self._driver: Driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
            max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
        )
        self._database = settings.NEO4J_DATABASE

    def verify_connectivity(self) -> None:
        """Raise if Neo4j is unreachable or credentials are wrong.

        Call this once at startup so a misconfigured connection fails loudly
        immediately, instead of surfacing as a confusing error on the first
        real query deep in a request.
        """
        try:
            self._driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", settings.NEO4J_URI)
        except ServiceUnavailable:
            logger.critical("Could not reach Neo4j at %s", settings.NEO4J_URI)
            raise

    def read(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        """Run a read-only Cypher query and return records as plain dicts."""
        result = self._driver.execute_query(
            cypher,
            parameters_=params,
            database_=self._database,
            routing_=RoutingControl.READ,
        )
        return [record.data() for record in result.records]

    def write(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        """Run a write Cypher query (CREATE/MERGE/etc.), returning any RETURNed records."""
        result = self._driver.execute_query(
            cypher,
            parameters_=params,
            database_=self._database,
            routing_=RoutingControl.WRITE,
        )
        return [record.data() for record in result.records]

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


@lru_cache
def get_neo4j_client() -> Neo4jClient:
    """Return the process-wide Neo4jClient singleton.

    The driver manages its own connection pool internally, so it should be
    created once and reused -- not re-instantiated per request.
    """
    return Neo4jClient()
