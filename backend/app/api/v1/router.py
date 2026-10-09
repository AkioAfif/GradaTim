"""Aggregator route for v1"""

from fastapi import APIRouter
from app.api.v1 import auth, goals, jadwal, tasks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(jadwal.router, prefix="/jadwal", tags=["jadwal"])
