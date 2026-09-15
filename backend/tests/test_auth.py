import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stockwise.app.main import app
from stockwise.app.db.base import Base
from stockwise.app.db.session import get_db
from stockwise.app.models.user import User
from stockwise.app.models.session import AuthSession
from stockwise.app.core.security import hash_token

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _no_rate_limit():
    from stockwise.app.core.limiter import limiter
    original = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = original


def _register_and_login(client, email="test@example.com"):
    client.post("/api/auth/register", json={
        "name": "Test User",
        "email": email,
        "password": "securepassword123",
        "password_confirm": "securepassword123",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "securepassword123",
    })
    return login_resp


class TestRegister:
    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        assert response.status_code == 201
        assert response.json()["message"] == "Kayıt başarılı"

    def test_register_duplicate_email(self, client):
        client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        response = client.post("/api/auth/register", json={
            "name": "Test User 2",
            "email": "test@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        assert response.status_code == 409

    def test_register_short_password(self, client):
        response = client.post("/api/auth/register", json={
            "name": "Test",
            "email": "test@example.com",
            "password": "short",
            "password_confirm": "short",
        })
        assert response.status_code == 422

    def test_register_password_mismatch(self, client):
        response = client.post("/api/auth/register", json={
            "name": "Test",
            "email": "test@example.com",
            "password": "securepassword123",
            "password_confirm": "differentpassword",
        })
        assert response.status_code == 422

    def test_register_stores_hashed_password(self, client):
        client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user is not None
        assert user.hashed_password != "securepassword123"
        assert user.hashed_password.startswith("$argon2")
        db.close()

    def test_register_normalizes_email(self, client):
        client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "  TEST@Example.COM  ",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == "test@example.com").first()
        assert user is not None
        db.close()


class TestLogin:
    def test_login_success(self, client):
        _register_and_login(client)
        client.cookies.clear()
        resp = _register_and_login(client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert "id" in data

    def test_login_sets_session_cookie(self, client):
        resp = _register_and_login(client)
        assert "sw_session" in resp.cookies
        assert "sw_csrf" in resp.cookies

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword123",
        })
        assert response.status_code == 401
        assert "hatalı" in response.json()["detail"]

    def test_login_nonexistent_email(self, client):
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "securepassword123",
        })
        assert response.status_code == 401


class TestMe:
    def test_me_authenticated(self, client):
        login_response = _register_and_login(client)
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_me_unauthenticated(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_session(self, client):
        client.cookies.set("sw_session", "invalidtoken123")
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client):
        _register_and_login(client)
        csrf = client.cookies.get("sw_csrf", "")
        response = client.post(
            "/api/auth/logout",
            headers={"x-csrf-token": csrf},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Çıkış yapıldı"

    def test_logout_invalidates_session(self, client):
        _register_and_login(client)
        csrf = client.cookies.get("sw_csrf", "")
        client.post(
            "/api/auth/logout",
            headers={"x-csrf-token": csrf},
        )
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_logout_rejected_without_csrf_token(self, client):
        _register_and_login(client)
        response = client.post("/api/auth/logout")
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

    def test_logout_rejected_with_mismatched_csrf(self, client):
        _register_and_login(client)
        response = client.post(
            "/api/auth/logout",
            headers={"x-csrf-token": "totally_wrong_value"},
        )
        assert response.status_code == 403

    def test_logout_rejected_with_header_only(self, client):
        _register_and_login(client)
        response = client.post(
            "/api/auth/logout",
            headers={"x-csrf-token": "some_value"},
        )
        assert response.status_code == 403

    def test_logout_rejected_with_cookie_only(self, client):
        _register_and_login(client)
        csrf = client.cookies.get("sw_csrf", "")
        # Send cookie but no header
        client.cookies.set("sw_csrf", csrf)
        response = client.post("/api/auth/logout")
        assert response.status_code == 403


class TestSessionExpiration:
    def test_expired_session_rejected(self, client):
        _register_and_login(client)

        db = TestingSessionLocal()
        token = client.cookies.get("sw_session", "")
        token_hash = hash_token(token)
        session_obj = db.query(AuthSession).filter(
            AuthSession.token_hash == token_hash
        ).first()
        if session_obj:
            session_obj.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
        db.close()

        response = client.get("/api/auth/me")
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


class TestSessionRevocation:
    def test_revoked_session_rejected(self, client):
        _register_and_login(client)

        db = TestingSessionLocal()
        token = client.cookies.get("sw_session", "")
        token_hash = hash_token(token)
        session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash).first()
        if session:
            from datetime import datetime, timezone
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
        db.close()

        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestHealthEndpoints:
    def test_health_still_works(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ready_still_works(self, client):
        response = client.get("/api/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


class TestRateLimiting:
    def _run_rate_limit_test(self, endpoint, payload, limit):
        from stockwise.app.core.limiter import limiter as shared_limiter
        from limits.storage import MemoryStorage

        original_enabled = shared_limiter.enabled
        original_storage = shared_limiter._storage
        shared_limiter.enabled = True
        shared_limiter._storage = MemoryStorage()
        try:
            with TestClient(app) as c:
                for i in range(limit):
                    resp = c.post(endpoint, json={
                        **payload,
                        "email": f"user{i}@example.com",
                    })
                    assert resp.status_code in (200, 201, 409), (
                        f"Request {i} should succeed, got {resp.status_code}"
                    )
                response = c.post(endpoint, json={
                    **payload,
                    "email": f"user{limit}@example.com",
                })
                assert response.status_code == 429
        finally:
            shared_limiter.enabled = original_enabled
            shared_limiter._storage = original_storage

    def test_register_rate_limit_returns_429(self):
        self._run_rate_limit_test(
            "/api/auth/register",
            {
                "name": "Rate Limit User",
                "password": "securepassword123",
                "password_confirm": "securepassword123",
            },
            limit=5,
        )

    def test_login_rate_limit_returns_429(self):
        from stockwise.app.core.limiter import limiter as shared_limiter
        from limits.storage import MemoryStorage

        original_enabled = shared_limiter.enabled
        original_storage = shared_limiter._storage
        shared_limiter.enabled = True
        shared_limiter._storage = MemoryStorage()
        try:
            with TestClient(app) as c:
                c.post("/api/auth/register", json={
                    "name": "Rate Limit User",
                    "email": "ratelimit_login@example.com",
                    "password": "securepassword123",
                    "password_confirm": "securepassword123",
                })
                for i in range(10):
                    resp = c.post("/api/auth/login", json={
                        "email": "ratelimit_login@example.com",
                        "password": "wrongpassword",
                    })
                    assert resp.status_code == 401, (
                        f"Login attempt {i} should fail with 401, got {resp.status_code}"
                    )
                response = c.post("/api/auth/login", json={
                    "email": "ratelimit_login@example.com",
                    "password": "wrongpassword",
                })
                assert response.status_code == 429
        finally:
            shared_limiter.enabled = original_enabled
            shared_limiter._storage = original_storage


class TestUntrustedOrigin:
    UNTRUSTED = "https://evil.example"
    TRUSTED = "http://localhost:5173"

    def _count_users(self):
        db = TestingSessionLocal()
        count = db.query(User).count()
        db.close()
        return count

    def _has_session_cookie(self, response):
        return "sw_session" in response.cookies

    # --- Preflight (OPTIONS) ---

    def test_preflight_untrusted_origin_rejected(self, client):
        response = client.options(
            "/api/auth/register",
            headers={
                "Origin": self.UNTRUSTED,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_trusted_origin_accepted(self, client):
        response = client.options(
            "/api/auth/register",
            headers={
                "Origin": self.TRUSTED,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.headers.get("access-control-allow-origin") == self.TRUSTED

    # --- Register from untrusted origin ---

    def test_register_untrusted_json_rejected(self, client):
        before = self._count_users()
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Evil User",
                "email": "evil_json@example.com",
                "password": "securepassword123",
                "password_confirm": "securepassword123",
            },
            headers={"Origin": self.UNTRUSTED},
        )
        after = self._count_users()
        assert response.status_code == 403
        assert after == before
        assert not self._has_session_cookie(response)

    def test_register_untrusted_form_urlencoded_rejected(self, client):
        before = self._count_users()
        response = client.post(
            "/api/auth/register",
            content="name=Evil+User&email=evil_form%40example.com&password=securepassword123&password_confirm=securepassword123",
            headers={
                "Origin": self.UNTRUSTED,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        after = self._count_users()
        assert response.status_code == 403
        assert after == before

    def test_register_untrusted_text_plain_rejected(self, client):
        before = self._count_users()
        response = client.post(
            "/api/auth/register",
            content='{"name":"Evil","email":"evil_tp@example.com","password":"securepassword123","password_confirm":"securepassword123"}',
            headers={
                "Origin": self.UNTRUSTED,
                "Content-Type": "text/plain",
            },
        )
        after = self._count_users()
        assert response.status_code == 403
        assert after == before

    def test_register_untrusted_multipart_rejected(self, client):
        before = self._count_users()
        response = client.post(
            "/api/auth/register",
            files={"file": ("test.txt", b"data", "text/plain")},
            headers={"Origin": self.UNTRUSTED},
        )
        after = self._count_users()
        assert response.status_code == 403
        assert after == before

    def test_register_untrusted_no_content_type_rejected(self, client):
        before = self._count_users()
        response = client.post(
            "/api/auth/register",
            content=b'{"name":"Evil","email":"evil_nct@example.com","password":"securepassword123","password_confirm":"securepassword123"}',
            headers={"Origin": self.UNTRUSTED},
        )
        after = self._count_users()
        assert response.status_code == 403
        assert after == before

    # --- Login from untrusted origin ---

    def test_login_untrusted_json_rejected(self, client):
        client.post("/api/auth/register", json={
            "name": "Login User",
            "email": "login_trust@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        response = client.post(
            "/api/auth/login",
            json={
                "email": "login_trust@example.com",
                "password": "securepassword123",
            },
            headers={"Origin": self.UNTRUSTED},
        )
        assert response.status_code == 403
        assert not self._has_session_cookie(response)

    def test_login_untrusted_form_urlencoded_rejected(self, client):
        client.post("/api/auth/register", json={
            "name": "Login User",
            "email": "login_form@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        response = client.post(
            "/api/auth/login",
            content="email=login_form%40example.com&password=securepassword123",
            headers={
                "Origin": self.UNTRUSTED,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        assert response.status_code == 403
        assert not self._has_session_cookie(response)

    def test_login_untrusted_text_plain_rejected(self, client):
        client.post("/api/auth/register", json={
            "name": "Login User",
            "email": "login_tp@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        response = client.post(
            "/api/auth/login",
            content='{"email":"login_tp@example.com","password":"securepassword123"}',
            headers={
                "Origin": self.UNTRUSTED,
                "Content-Type": "text/plain",
            },
        )
        assert response.status_code == 403
        assert not self._has_session_cookie(response)

    def test_login_untrusted_no_content_type_rejected(self, client):
        client.post("/api/auth/register", json={
            "name": "Login User",
            "email": "login_nct@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        response = client.post(
            "/api/auth/login",
            content=b'{"email":"login_nct@example.com","password":"securepassword123"}',
            headers={"Origin": self.UNTRUSTED},
        )
        assert response.status_code == 403
        assert not self._has_session_cookie(response)

    # --- Trusted origin still works ---

    def test_register_trusted_origin_json_succeeds(self, client):
        before = self._count_users()
        response = client.post(
            "/api/auth/register",
            json={
                "name": "Trusted User",
                "email": "trusted@example.com",
                "password": "securepassword123",
                "password_confirm": "securepassword123",
            },
            headers={"Origin": self.TRUSTED},
        )
        after = self._count_users()
        assert response.status_code == 201
        assert after == before + 1
        assert response.headers.get("access-control-allow-origin") == self.TRUSTED

    def test_login_trusted_origin_json_succeeds(self, client):
        client.post("/api/auth/register", json={
            "name": "Trusted User",
            "email": "trusted_login@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        response = client.post(
            "/api/auth/login",
            json={
                "email": "trusted_login@example.com",
                "password": "securepassword123",
            },
            headers={"Origin": self.TRUSTED},
        )
        assert response.status_code == 200
        assert self._has_session_cookie(response)
        assert response.headers.get("access-control-allow-origin") == self.TRUSTED

    def test_no_origin_header_succeeds(self, client):
        before = self._count_users()
        response = client.post(
            "/api/auth/register",
            json={
                "name": "No Origin User",
                "email": "no_origin@example.com",
                "password": "securepassword123",
                "password_confirm": "securepassword123",
            },
        )
        after = self._count_users()
        assert response.status_code == 201
        assert after == before + 1
