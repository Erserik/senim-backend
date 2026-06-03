import pytest


async def _token(client, phone="+77001234567"):
    res = await client.post("/api/auth/login", json={"phone": phone})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_change_phone_without_code(client):
    token = await _token(client)
    res = await client.post(
        "/api/auth/change-phone",
        json={"phone": "8 (700) 765-43-21"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["phone"] == "+77007654321"


@pytest.mark.asyncio
async def test_change_phone_taken_400(client):
    await _token(client, "+77007654321")          # занимаем номер
    token = await _token(client, "+77001234567")  # другой юзер
    res = await client.post(
        "/api/auth/change-phone",
        json={"phone": "+77007654321"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_change_phone_invalid_400(client):
    token = await _token(client)
    res = await client.post(
        "/api/auth/change-phone",
        json={"phone": "12345"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
