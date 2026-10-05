"""Pytest configuration and fixtures for test isolation.

Each test function gets a fresh isolated in-memory SQLite database.
Tests do not depend on execution order or developer's real database.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.database import Base, get_db
from app.db.models import Vehicle, Telemetry, Simulation
from app.core.config import DEMO_VEHICLE_CONFIG
from app.main import app


@pytest.fixture(scope="function")
def test_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create fresh database tables and session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()

    # Seed demo vehicle
    demo_vehicle = Vehicle(**DEMO_VEHICLE_CONFIG)
    db.add(demo_vehicle)
    db.commit()

    yield db

    # Cleanup
    db.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_engine, test_db):
    """Create test client with isolated database."""
    # Override database dependency
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear override
    app.dependency_overrides.clear()


@pytest.fixture
def demo_vehicle_id():
    """Return the demo vehicle ID."""
    return DEMO_VEHICLE_CONFIG["vehicle_id"]


@pytest.fixture
def demo_vehicle_config():
    """Return the full demo vehicle configuration."""
    return DEMO_VEHICLE_CONFIG.copy()


# ============================================================
# Sprint 4 (AI layer) shared fixtures
# ============================================================

@pytest.fixture(autouse=True)
def _skip_real_ollama_startup_probe(monkeypatch):
    """Every test that builds a TestClient also runs a fresh app startup, and
    the real Sprint 4 startup health check makes a genuine network call to
    Ollama on each one. On this machine that call is slow enough (sub-second
    to several seconds, observed empirically) to add minutes across the full
    suite, even though Ollama responds successfully every time. It has no
    bearing on correctness -- the Ollama adapter itself and the lazy
    per-request availability check are covered directly by the dedicated,
    mocked `mock_ollama_*` fixtures below -- so the background probe is
    replaced with a no-op for the whole test session.
    """
    import app.main as main_module

    async def _noop() -> None:
        return None

    monkeypatch.setattr(main_module, "_log_ollama_availability", _noop)


@pytest.fixture
def run_normal_driving(client, demo_vehicle_id):
    """Run a NORMAL_DRIVING simulation and return the response."""
    response = client.post("/api/v1/simulation/run", json={
        "vehicle_id": demo_vehicle_id,
        "scenario": "NORMAL_DRIVING",
        "duration_minutes": 10,
        "interval_seconds": 10,
        "seed": 42,
        "mode": "fresh",
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def run_aggressive_driving(client, demo_vehicle_id, run_normal_driving):
    """Run an AGGRESSIVE_DRIVING simulation after NORMAL_DRIVING."""
    response = client.post("/api/v1/simulation/run", json={
        "vehicle_id": demo_vehicle_id,
        "scenario": "AGGRESSIVE_DRIVING",
        "duration_minutes": 10,
        "interval_seconds": 10,
        "seed": 42,
        "mode": "fresh",
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def mock_ollama_unavailable(monkeypatch):
    """Make the AI layer behave as if Ollama cannot be reached at all."""
    import app.ai.service as ai_service

    async def _unavailable(*args, **kwargs):
        return False

    monkeypatch.setattr(ai_service, "check_ollama_available", _unavailable)
    return True


@pytest.fixture
def mock_ollama_answer(monkeypatch):
    """Make the AI layer report Ollama available and return a fixed, valid answer.

    Returns a function the test can call with the desired answer text.
    """
    import app.ai.service as ai_service

    captured_messages: list = []

    def _install(answer_text: str = "This is a mocked Ollama answer."):
        async def _available(*args, **kwargs):
            return True

        async def _chat(messages, **kwargs):
            captured_messages.append(messages)
            import json
            return json.dumps({"answer": answer_text})

        monkeypatch.setattr(ai_service, "check_ollama_available", _available)
        monkeypatch.setattr(ai_service, "chat", _chat)
        return captured_messages

    return _install


@pytest.fixture
def mock_ollama_malformed(monkeypatch):
    """Make the AI layer report Ollama available but return unusable output."""
    import app.ai.service as ai_service

    def _install(raw_text: str = "not json at all"):
        async def _available(*args, **kwargs):
            return True

        async def _chat(messages, **kwargs):
            return raw_text

        monkeypatch.setattr(ai_service, "check_ollama_available", _available)
        monkeypatch.setattr(ai_service, "chat", _chat)

    return _install
