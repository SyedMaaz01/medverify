"""Tests for authentication API endpoints."""
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_manufacturer(client: AsyncClient):
    """Test manufacturer registration."""
    payload = {
        "name": "New Pharma Co",
        "drap_license_no": f"DRAP-{uuid.uuid4().hex[:8]}",
        "contact_email": "contact@newpharma.com",
        "contact_phone": "+92-300-9876543",
        "password": "SecureP@123",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Pharma Co"
    assert data["drap_license_no"] == payload["drap_license_no"]
    assert data["is_active"] is True
    assert data["role"] == "manufacturer"


@pytest.mark.asyncio
async def test_register_duplicate_drap_license(client: AsyncClient):
    """Test registration with duplicate DRAP license fails."""
    payload = {
        "name": "Pharma A",
        "drap_license_no": "DRAP-DUP-001",
        "contact_email": "a@pharma.com",
        "password": "SecureP@123",
    }
    response1 = await client.post("/api/auth/register", json=payload)
    assert response1.status_code == 201

    payload["name"] = "Pharma B"
    payload["contact_email"] = "b@pharma.com"
    response2 = await client.post("/api/auth/register", json=payload)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email fails."""
    drap1 = f"DRAP-{uuid.uuid4().hex[:8]}"
    drap2 = f"DRAP-{uuid.uuid4().hex[:8]}"

    payload1 = {"name": "A", "drap_license_no": drap1, "contact_email": "dup@test.com", "password": "SecureP@123"}
    payload2 = {"name": "B", "drap_license_no": drap2, "contact_email": "dup@test.com", "password": "SecureP@456"}

    await client.post("/api/auth/register", json=payload1)
    response = await client.post("/api/auth/register", json=payload2)
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login returns tokens."""
    drap = f"DRAP-{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "name": "Login Pharma",
        "drap_license_no": drap,
        "contact_email": "login@test.com",
        "password": "MySecureP@1",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_payload = {"drap_license_no": drap, "password": "MySecureP@1"}
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["manufacturer"]["drap_license_no"] == drap


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password fails."""
    drap = f"DRAP-{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "name": "Wrong Pass Pharma",
        "drap_license_no": drap,
        "password": "CorrectP@123",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_payload = {"drap_license_no": drap, "password": "WrongP@123"}
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_manufacturer(client: AsyncClient):
    """Test login with nonexistent DRAP license fails."""
    login_payload = {"drap_license_no": "DRAP-NONEXISTENT", "password": "SecureP@123"}
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient):
    """Test getting authenticated user profile."""
    drap = f"DRAP-{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "name": "Profile Pharma",
        "drap_license_no": drap,
        "contact_email": "profile@test.com",
        "password": "SecureP@123",
    }
    reg_response = await client.post("/api/auth/register", json=reg_payload)
    assert reg_response.status_code == 201

    login_response = await client.post("/api/auth/login", json={"drap_license_no": drap, "password": "SecureP@123"})
    token = login_response.json()["access_token"]

    profile_response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["drap_license_no"] == drap


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """Test getting profile without token fails."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    """Test password change."""
    drap = f"DRAP-{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "name": "PassChange Pharma",
        "drap_license_no": drap,
        "password": "OldP@ss123",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_response = await client.post("/api/auth/login", json={"drap_license_no": drap, "password": "OldP@ss123"})
    token = login_response.json()["access_token"]

    change_response = await client.put(
        "/api/auth/me/password",
        json={"current_password": "OldP@ss123", "new_password": "NewP@ss456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_response.status_code == 200

    # Old password should no longer work
    old_login = await client.post("/api/auth/login", json={"drap_license_no": drap, "password": "OldP@ss123"})
    assert old_login.status_code == 401

    # New password should work
    new_login = await client.post("/api/auth/login", json={"drap_license_no": drap, "password": "NewP@ss456"})
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Test token refresh."""
    drap = f"DRAP-{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "name": "Refresh Pharma",
        "drap_license_no": drap,
        "password": "SecureP@123",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_response = await client.post("/api/auth/login", json={"drap_license_no": drap, "password": "SecureP@123"})
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Test logout."""
    drap = f"DRAP-{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "name": "Logout Pharma",
        "drap_license_no": drap,
        "password": "SecureP@123",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_response = await client.post("/api/auth/login", json={"drap_license_no": drap, "password": "SecureP@123"})
    token = login_response.json()["access_token"]

    logout_response = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    """Test profile update."""
    drap = f"DRAP-{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "name": "Update Pharma",
        "drap_license_no": drap,
        "contact_email": "update@test.com",
        "password": "SecureP@123",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_response = await client.post("/api/auth/login", json={"drap_license_no": drap, "password": "SecureP@123"})
    token = login_response.json()["access_token"]

    update_response = await client.put(
        "/api/auth/me",
        json={"name": "Updated Pharma", "contact_phone": "+92-321-6543210"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Pharma"
    assert update_response.json()["contact_phone"] == "+92-321-6543210"
