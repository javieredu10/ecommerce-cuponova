"""
Tests de integración para el Auth Service.
Ejecutar con: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.find_by_email.return_value = None
    repo.save.side_effect = lambda u: u
    return repo


@pytest.fixture
def mock_token_cache():
    cache = AsyncMock()
    cache.get_refresh_token.return_value = None
    return cache


# ─── Tests de dominio ────────────────────────────────────────────────────────

def test_user_creation():
    from src.domain.entities.user import User, UserRole, OAuthProvider
    from datetime import datetime

    user = User.create(
        tenant_id="tenant-001",
        email="test@example.com",
        hashed_password="hashed_pw",
        roles=[UserRole.CLIENT],
    )
    assert user.email == "test@example.com"
    assert user.tenant_id == "tenant-001"
    assert UserRole.CLIENT in user.roles
    assert user.is_active is True
    assert user.oauth_provider == OAuthProvider.LOCAL


def test_user_has_role():
    from src.domain.entities.user import User, UserRole

    user = User.create(
        tenant_id="t1",
        email="admin@test.com",
        roles=[UserRole.ADMIN, UserRole.CLIENT],
    )
    assert user.has_role(UserRole.ADMIN) is True
    assert user.has_role(UserRole.PROVIDER) is False


# ─── Tests de casos de uso ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_use_case_success(mock_user_repo):
    from src.application.use_cases.auth_use_cases import RegisterUseCase
    from src.application.dtos import RegisterRequest

    uc = RegisterUseCase(mock_user_repo)
    req = RegisterRequest(
        tenant_id="tenant-001",
        email="nuevo@example.com",
        password="Password123!",
    )
    user = await uc.execute(req)
    assert user.email == "nuevo@example.com"
    assert user.hashed_password is not None
    assert user.hashed_password != "Password123!"
    mock_user_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(mock_user_repo):
    from src.application.use_cases.auth_use_cases import RegisterUseCase
    from src.application.dtos import RegisterRequest
    from src.domain.entities.user import User
    from fastapi import HTTPException
    from datetime import datetime

    existing = User.create("t1", "existe@test.com")
    mock_user_repo.find_by_email.return_value = existing

    uc = RegisterUseCase(mock_user_repo)
    req = RegisterRequest(tenant_id="t1", email="existe@test.com", password="pw")

    with pytest.raises(HTTPException) as exc:
        await uc.execute(req)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_login_invalid_password(mock_user_repo, mock_token_cache):
    from src.application.use_cases.auth_use_cases import LoginUseCase
    from src.application.dtos import LoginRequest
    from src.domain.entities.user import User
    from fastapi import HTTPException
    import bcrypt

    user = User.create("t1", "user@test.com",
                       hashed_password=bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode())
    mock_user_repo.find_by_email.return_value = user

    uc = LoginUseCase(mock_user_repo, mock_token_cache)
    req = LoginRequest(tenant_id="t1", email="user@test.com", password="wrong")

    with pytest.raises(HTTPException) as exc:
        await uc.execute(req)
    assert exc.value.status_code == 401


# ─── Tests de API HTTP ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "auth-service"
