"""Tests for authentication endpoints (register, login)."""

# Strong password that meets all complexity requirements
STRONG_PASSWORD = "SecurePass123!"


def test_register_new_user(client):
    """Should create a new user and return their info."""
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": STRONG_PASSWORD,
        "full_name": "Test User",
    })
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data
    # Password should NOT be in the response
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client):
    """Should reject duplicate email registration."""
    # Register once
    client.post("/api/v1/auth/register", json={
        "email": "dupe@example.com",
        "password": STRONG_PASSWORD,
    })
    # Try again with same email
    response = client.post("/api/v1/auth/register", json={
        "email": "dupe@example.com",
        "password": STRONG_PASSWORD,
    })
    assert response.status_code == 400
    # Anti-enumeration: generic message, no "already registered"
    assert "detail" in response.json()


def test_register_short_password(client):
    """Should reject passwords shorter than 12 characters."""
    response = client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "password": "short",
    })
    assert response.status_code == 422  # Validation error


def test_register_weak_password_no_uppercase(client):
    """Should reject passwords without uppercase letter."""
    response = client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "securepass123!",
    })
    assert response.status_code == 400
    assert "uppercase" in response.json()["detail"]


def test_register_weak_password_no_special(client):
    """Should reject passwords without special character."""
    response = client.post("/api/v1/auth/register", json={
        "email": "weak2@example.com",
        "password": "SecurePass1234",
    })
    assert response.status_code == 400
    assert "special" in response.json()["detail"]


def test_login_success(client):
    """Should return a JWT token on successful login."""
    # Register first
    client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": STRONG_PASSWORD,
    })
    # Login
    response = client.post("/api/v1/auth/login", data={
        "username": "login@example.com",
        "password": STRONG_PASSWORD,
    })
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Should reject incorrect password."""
    # Register
    client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com",
        "password": STRONG_PASSWORD,
    })
    # Login with wrong password
    response = client.post("/api/v1/auth/login", data={
        "username": "wrong@example.com",
        "password": "WrongPassword123!",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Should reject login for non-existent user."""
    response = client.post("/api/v1/auth/login", data={
        "username": "nobody@example.com",
        "password": STRONG_PASSWORD,
    })
    assert response.status_code == 401


def test_get_profile_with_token(client):
    """Should return user profile when authenticated."""
    # Register
    client.post("/api/v1/auth/register", json={
        "email": "profile@example.com",
        "password": STRONG_PASSWORD,
        "full_name": "Profile User",
    })
    # Login to get token
    login_resp = client.post("/api/v1/auth/login", data={
        "username": "profile@example.com",
        "password": STRONG_PASSWORD,
    })
    token = login_resp.json()["access_token"]

    # Get profile
    response = client.get("/api/v1/user/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "profile@example.com"


def test_get_profile_without_token(client):
    """Should reject profile access without authentication."""
    response = client.get("/api/v1/user/me")
    assert response.status_code == 401
