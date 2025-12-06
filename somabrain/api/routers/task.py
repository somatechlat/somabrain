"""API endpoints for Dynamic Task Registry."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from somabrain.api.dependencies.auth import auth_guard
from somabrain.api.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TaskListResponse,
)
from somabrain.storage.task_registry import TaskRegistryStore

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Lazy singleton pattern used in other routers
_task_store: Optional[TaskRegistryStore] = None

def get_task_store() -> TaskRegistryStore:
    global _task_store
    if _task_store is None:
        _task_store = TaskRegistryStore()
    return _task_store

@router.post("/register", response_model=TaskResponse)
async def register_task(
    payload: TaskCreate,
    auth=Depends(auth_guard),
    store: TaskRegistryStore = Depends(get_task_store),
):
    """Register a new task definition."""

    # Check for existing task with same name
    existing = store.get_by_name(payload.name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Task with name '{payload.name}' already exists"
        )

    try:
        task = store.create(payload)
        return TaskResponse.model_validate(task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    auth=Depends(auth_guard),
    store: TaskRegistryStore = Depends(get_task_store),
):
    """List registered tasks."""
    tasks, total = store.list(limit=limit, offset=offset)
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total
    )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    auth=Depends(auth_guard),
    store: TaskRegistryStore = Depends(get_task_store),
):
    """Get a specific task definition."""
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    auth=Depends(auth_guard),
    store: TaskRegistryStore = Depends(get_task_store),
):
    """Update a task definition."""
    task = store.update(task_id, payload)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    auth=Depends(auth_guard),
    store: TaskRegistryStore = Depends(get_task_store),
):
    """Delete a task definition."""
    success = store.delete(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}
