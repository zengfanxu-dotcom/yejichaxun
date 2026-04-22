from collections.abc import Generator
import sys
import types

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 测试阶段不需要真实初始化 RAG 向量系统，避免导入时触发本地模型依赖。
rag_runtime_stub = types.ModuleType("backend.app.core.tools.rag_runtime")
rag_runtime_stub.query_topk_context = lambda tender_text: ""
rag_runtime_stub.query_top1_context = lambda query: ""
rag_runtime_stub.rebuild_rag_index = lambda: 0
rag_runtime_stub.get_active_slot = lambda: "A"
sys.modules["backend.app.core.tools.rag_runtime"] = rag_runtime_stub

from backend.app.api.v1.endpoints import analyze as analyze_endpoint
from backend.app.api.v1.endpoints import ws_tasks as ws_tasks_endpoint
from backend.app.db.models import Base
from backend.app.db.session import get_db
from backend.app.main import app


@pytest.fixture()
def db_session_factory(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        yield testing_session_local
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, db_session_factory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr("backend.app.main.init_db", lambda: None)
    monkeypatch.setattr(analyze_endpoint, "SessionLocal", db_session_factory)
    monkeypatch.setattr(ws_tasks_endpoint, "SessionLocal", db_session_factory)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
