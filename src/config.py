from enum import Enum
import logging
import re
from typing import Self
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class EnvironmentOption(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Core Application Settings
    # ------------------------------------------------------------------
    ENV: EnvironmentOption = Field(
        default=EnvironmentOption.DEVELOPMENT,
        description="Application execution environment.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )

    # ------------------------------------------------------------------
    # Google Vertex AI Configuration
    # ------------------------------------------------------------------
    GOOGLE_CLOUD_PROJECT: str = Field(
        ...,
        description="GCP Project ID required for Vertex AI services.",
    )
    GOOGLE_CLOUD_REGION: str = Field(
        default="us-central1",
        description="GCP Region where Vertex AI resources are provisioned.",
    )
    EMBEDDING_MODEL_NAME: str = Field(
        default="text-embedding-004",
        description="Vertex AI embedding model identifier.",
    )
    LLM_MODEL_NAME: str = Field(
        default="gemini-1.5-pro",
        description="Vertex AI Gemini model identifier for the agent.",
    )

    # ------------------------------------------------------------------
    # Neo4j Graph Database Settings
    # ------------------------------------------------------------------
    # Set to 'bolt://neo4j:7687' if running inside Docker network, or 'bolt://localhost:7687' if on host.
    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI.",
    )
    NEO4J_USER: str = Field(
        default="neo4j",
        description="Neo4j authentication username.",
    )
    NEO4J_PASSWORD: SecretStr = Field(
        default=SecretStr("password123"),
        description="Neo4j authentication password.",
    )
    NEO4J_AUTH: str | None = Field(
        default=None,
        description="Optional NEO4J_AUTH string from docker-compose (e.g. neo4j/password123).",
    )
    NEO4J_DATABASE: str = Field(
        default="neo4j",
        description="Target Neo4j database instance name.",
    )
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = Field(
        default=1,  # increse in prod
        ge=1,
        le=500,
        description="Maximum connection pool size for the Neo4j driver.",
    )

    # ------------------------------------------------------------------
    # Qdrant Vector Database Settings
    # ------------------------------------------------------------------
    # Set to 'qdrant' if running inside Docker network, or 'localhost' if on host.
    QDRANT_HOST: str = Field(
        default="localhost",
        description="Qdrant server hostname.",
    )
    QDRANT_PORT: int = Field(
        default=6333,
        ge=1,
        le=65535,
        description="Qdrant REST API port.",
    )
    QDRANT_GRPC_PORT: int = Field(
        default=6334,
        ge=1,
        le=65535,
        description="Qdrant gRPC API port.",
    )
    QDRANT_API_KEY: SecretStr | None = Field(
        default=None,
        description="API Key for Qdrant Cloud or protected instances.",
    )
    QDRANT_COLLECTION_NAME: str = Field(
        default="agentic_graph_rag",
        description="Vector collection name for document embeddings.",
    )
    QDRANT_VECTOR_SIZE: int = Field(
        default=768,
        gt=0,
        description="Dimensionality of text embeddings.",
    )
    QDRANT_USE_GRPC: bool = Field(
        default=True,
        description="Toggle gRPC interface for low-latency queries.",
    )

    # ------------------------------------------------------------------
    # Field Validators & Normalizers
    # ------------------------------------------------------------------
    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL '{v}'. Must be one of: {', '.join(valid_levels)}"
            )
        return upper_v

    @field_validator("NEO4J_URI")
    @classmethod
    def validate_neo4j_uri(cls, v: str) -> str:
        allowed_schemes = (
            "bolt://",
            "neo4j://",
            "bolt+s://",
            "neo4j+s://",
            "bolt+ssc://",
            "neo4j+ssc://",
        )
        if not any(v.startswith(scheme) for scheme in allowed_schemes):
            raise ValueError(
                f"Invalid NEO4J_URI schema '{v}'. Must start with one of: {', '.join(allowed_schemes)}"
            )
        return v

    # ------------------------------------------------------------------
    # Model-Level Validation & Syncing
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def sync_neo4j_auth_and_guards(self) -> Self:
        """Parses NEO4J_AUTH if present and enforces security constraints."""
        # Auto-extract username and password if NEO4J_AUTH (user/pass format) is provided
        if self.NEO4J_AUTH and "/" in self.NEO4J_AUTH:
            user, pwd = self.NEO4J_AUTH.split("/", 1)
            if user:
                self.NEO4J_USER = user
            if pwd:
                self.NEO4J_PASSWORD = SecretStr(pwd)

        # Enforce strong security standards for Staging/Production environments
        if self.ENV in (EnvironmentOption.PRODUCTION, EnvironmentOption.STAGING):
            raw_neo4j_pwd = self.NEO4J_PASSWORD.get_secret_value()
            if raw_neo4j_pwd in ("neo4j", "password", "password123", "admin"):
                raise ValueError(
                    f"Insecure default NEO4J_PASSWORD used in {self.ENV.value} mode. "
                    "Please set a strong, custom password."
                )

            if self.ENV == EnvironmentOption.PRODUCTION and self.LOG_LEVEL == "DEBUG":
                logger.warning(
                    "LOG_LEVEL is set to DEBUG in PRODUCTION mode. "
                    "Consider raising to INFO or WARNING."
                )
        return self

    # ------------------------------------------------------------------
    # Dynamic Property Helpers
    # ------------------------------------------------------------------
    @property
    def QDRANT_URL(self) -> str:
        """Constructs full Qdrant HTTP connection URL."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


# Global Singleton Configuration Instance
try:
    settings = Settings()
except Exception as e:
    logger.critical(
        "Failed to initialize configuration settings due to validation errors."
    )
    raise e
