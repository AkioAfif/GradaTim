import os

base_dir = r"d:\Akio\Senpro\GradaTim\backend"

files_to_create = {
    "app/api/v1/auth.py": '"""FR-1: Auth & User Profile"""\n\nfrom fastapi import APIRouter\n\nrouter = APIRouter()\n',
    "app/api/v1/goals.py": '"""FR-2: AI Goal Decomposition & CRUD"""\n\nfrom fastapi import APIRouter\n\nrouter = APIRouter()\n',
    "app/api/v1/tasks.py": '"""FR-3 & FR-4: Today Action List & Progress Tracker"""\n\nfrom fastapi import APIRouter\n\nrouter = APIRouter()\n',
    "app/api/v1/router.py": '"""Aggregator route for v1"""\n\nfrom fastapi import APIRouter\nfrom app.api.v1 import auth, goals, tasks\n\napi_router = APIRouter()\napi_router.include_router(auth.router, prefix="/auth", tags=["auth"])\napi_router.include_router(goals.router, prefix="/goals", tags=["goals"])\napi_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])\n',
    "app/api/deps.py": '"""Dependency injection (DB session, auth check)"""\n',
    "app/core/config.py": '"""Pydantic Settings (.env loader)"""\n\nfrom pydantic_settings import BaseSettings\n\nclass Settings(BaseSettings):\n    DATABASE_URL: str = "sqlite:///./test.db"\n    SECRET_KEY: str = "secret"\n    OPENAI_API_KEY: str | None = None\n\n    class Config:\n        env_file = ".env"\n\nsettings = Settings()\n',
    "app/core/security.py": '"""Password hashing / JWT token logic"""\n',
    "app/db/session.py": '"""DB engine & session generator"""\n\nfrom sqlalchemy import create_engine\nfrom sqlalchemy.orm import sessionmaker\nfrom app.core.config import settings\n\nengine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)\nSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n\ndef get_db():\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()\n',
    "app/db/init_db.py": '"""DB seeder / initial setup"""\n',
    "app/models/user.py": '"""SQLAlchemy / SQLModel entities - user.py"""\n',
    "app/models/goal.py": '"""SQLAlchemy / SQLModel entities - goal.py"""\n',
    "app/models/milestone.py": '"""SQLAlchemy / SQLModel entities - milestone.py"""\n',
    "app/models/task.py": '"""SQLAlchemy / SQLModel entities - task.py"""\n',
    "app/schemas/ai_decomposition.py": '"""AI JSON contract schema"""\n',
    "app/schemas/goal.py": '"""Pydantic request/response schemas - goal.py"""\n',
    "app/schemas/task.py": '"""Pydantic request/response schemas - task.py"""\n',
    "app/services/ai_service.py": '"""LLM integration & prompting logic"""\n',
    "app/services/goal_service.py": '"""Decomposition & scheduling business logic"""\n',
    "app/main.py": '"""FastAPI entry point"""\n\nfrom fastapi import FastAPI\nfrom app.api.v1.router import api_router\n\napp = FastAPI(title="GradaTim Backend API")\n\napp.include_router(api_router, prefix="/api/v1")\n',
    "requirements.txt": "fastapi\nuvicorn\nsqlalchemy\nalembic\npydantic\npydantic-settings\npython-jose\npasslib\npytest\n",
    ".env.example": "DATABASE_URL=postgresql://user:password@localhost:5432/db\nSECRET_KEY=your-super-secret-key\nOPENAI_API_KEY=your-openai-api-key\n",
    "Dockerfile": "FROM python:3.11-slim\n\nWORKDIR /app\n\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY . .\n\nCMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n",
    "tests/__init__.py": '"""Unit & integration tests (pytest)"""\n'
}

for rel_path, content in files_to_create.items():
    full_path = os.path.join(base_dir, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Scaffold created successfully.")
