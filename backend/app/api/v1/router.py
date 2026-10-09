"""Aggregator route for v1"""

from fastapi import APIRouter
from app.api.v1 import auth, goals, tasks, time_constraints

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(time_constraints.router, prefix="/time-constraints", tags=["time-constraints"])
