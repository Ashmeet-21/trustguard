"""Tests for authentication endpoints (register, login)."""


def test_register_new_user(client):
    """Should create a new user and return their info."""
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepass123",
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
        "password": "securepass123",
    })
    # Try again with same email
    response = client.post("/api/v1/auth/register", json={
        "email": "dupe@example.com",
        "password": "securepass123",
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_register_short_password(client):
    """Should reject passwords shorter than 8 characters."""
    response = client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "password": "short",
    })
    assert response.status_code == 422  # Validation error


def test_login_success(client):
    """Should return a JWT token on successful login."""
    # Register first
    client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "securepass123",
    })
    # Login
    response = client.post("/api/v1/auth/login", data={
        "username": "login@example.com",
        "password": "securepass123",
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
        "password": "securepass123",
    })
    # Login with wrong password
    response = client.post("/api/v1/auth/login", data={
        "username": "wrong@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Should reject login for non-existent user."""
    response = client.post("/api/v1/auth/login", data={
        "username": "nobody@example.com",
        "password": "securepass123",
    })
    assert response.status_code == 401


def test_get_profile_with_token(client):
    """Should return user profile when authenticated."""
    # Register
    client.post("/api/v1/auth/register", json={
        "email": "profile@example.com",
        "password": "securepass123",
        "full_name": "Profile User",
    })
    # Login to get token
    login_resp = client.post("/api/v1/auth/login", data={
        "username": "profile@example.com",
        "password": "securepass123",
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
