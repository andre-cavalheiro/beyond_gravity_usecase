# ruff: noqa: E402
import os

# import subprocess
import pytest
from fastapi_pagination import add_pagination

os.environ["FURY_API_APP_ENVIRONMENT"] = "test"
os.environ["FURY_DB_TENANT_ROLE_ENABLED"] = "false"
os.environ["FURY_API_DEVEX_ENABLED"] = "true"
os.environ["FURY_API_DEVEX_ON_CREATE_ORGANIZATION_SKIP_AUTH0_USER_CREATE"] = "true"
os.environ["FURY_API_DEVEX_SKIP_AUTH0_USER_CREATE"] = "true"
os.environ["FURY_API_DEVEX_ON_CREATE_ORGANIZATION_SKIP_DEFAULT_INTERNAL_USERS_VAULT_CREATION"] = "true"
os.environ["FURY_API_EVENTS_API_USE_BACKGROUND_TASKS"] = "false"

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import create_engine


@pytest.fixture(scope="session")
async def db_init() -> None:
    from fury_api.lib.db.base import metadata
    from fury_api.lib.settings import config

    engine = create_engine(config.database.URL, echo=True)
    with engine.connect() as connection:
        connection.execute(text("DROP VIEW IF EXISTS entities;"))
        connection.commit()

    metadata.drop_all(engine)
    metadata.create_all(engine)
    # TODO: run the migrations with alembic and add tests to the model query endpoint to ensure the view is used
    # subprocess.call("poetry run alembic --config alembic.ini upgrade head")


@pytest.fixture(scope="session")
async def app() -> FastAPI:
    from fury_api.domain.lifecycle import on_shutdown, on_startup
    from fury_api.main import app

    await on_startup()
    yield app
    await on_shutdown()


@pytest.fixture(scope="session")
def mocked_user_client(app: FastAPI) -> TestClient:
    from fury_api.domain.users.models import User
    from fury_api.domain.security import get_current_user, get_current_user_new_organization, validate_api_key

    app.dependency_overrides[get_current_user] = lambda: User(
        source_id="1", name="test", email="test@test.com", organization_id=1, user_id=1
    )
    app.dependency_overrides[get_current_user_new_organization] = lambda: User(
        source_id="1", name="test", email="test@test.com", organization_id=None, user_id=None
    )
    app.dependency_overrides[validate_api_key] = lambda: None

    class VaultClient:
        def read(self, secret: str):
            return None

        def create(self, secret: str, data: dict):
            return None

        def decrypt(self, secret: str):
            return None

    add_pagination(app)

    return TestClient(app)


@pytest.fixture(scope="session")
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
async def bootstrap_org(db_init: None, mocked_user_client: TestClient) -> None:
    response = mocked_user_client.post("/api/v1/organizations", json={"name": "test-org"})
    # Assuming the function is imported and ready to be used
    # Retrieve the UnitOfWork dependency
    assert response.status_code == 201, response.json()


@pytest.fixture(scope="function")
def use_system_user(mocked_user_client: TestClient) -> None:
    from fury_api.domain.dependencies import is_system_user

    mocked_user_client.app.dependency_overrides[is_system_user] = lambda: True
    yield
    del mocked_user_client.app.dependency_overrides[is_system_user]
