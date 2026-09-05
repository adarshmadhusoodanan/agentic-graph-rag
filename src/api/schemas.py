"""Pydantic request/response models for the API.

Kept separate from the route handlers so the API's public contract is
visible in one file, independent of how any given endpoint is implemented.
"""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str


class HealthResponse(BaseModel):
    status: str