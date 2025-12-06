"""Pydantic schemas for Dynamic Task Registry."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    name: str = Field(..., max_length=128, description="Unique name of the task")
    description: Optional[str] = Field(None, max_length=512)
    schema: Dict[str, Any] = Field(..., description="JSON Schema for task parameters")
    version: str = Field("1.0.0", max_length=32)
    rate_limit_per_min: Optional[int] = Field(60, description="Requests per minute allowed")
    policy_tags: Optional[Dict[str, Any]] = Field(None, description="OPA policy tags")

class TaskUpdate(BaseModel):
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    version: Optional[str] = None
    rate_limit_per_min: Optional[int] = None
    policy_tags: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    schema: Dict[str, Any] = Field(alias="schema_")  # Avoid collision if schema is a reserved keyword
    version: str
    rate_limit_per_min: Optional[int]
    policy_tags: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
