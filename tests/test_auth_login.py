from app.core.phone import normalize_phone


def test_normalize_phone_variants():
    assert normalize_phone("+77001234567") == "+77001234567"
    assert normalize_phone("87001234567") == "+77001234567"
    assert normalize_phone("77001234567") == "+77001234567"
    assert normalize_phone("7001234567") == "+77001234567"
    assert normalize_phone("8 (700) 123-45-67") == "+77001234567"
    assert normalize_phone("12345") is None
    assert normalize_phone("") is None
    assert normalize_phone("+15551234567") is None
    assert normalize_phone("3105551234") is None
    assert normalize_phone(None) is None


async def test_login_creates_new_user(client):
    res = await client.post("/api/auth/login", json={"phone": "+77001234567"})
    assert res.status_code == 200
    body = res.json()
    assert body["is_new_user"] is True
    assert body["access_token"]


async def test_login_existing_user_not_new(client):
    first = await client.post("/api/auth/login", json={"phone": "+77001234567"})
    second = await client.post("/api/auth/login", json={"phone": "+77001234567"})
    assert second.json()["is_new_user"] is False


async def test_login_normalizes_8_prefix_to_same_user(client):
    a = await client.post("/api/auth/login", json={"phone": "+77001234567"})
    b = await client.post("/api/auth/login", json={"phone": "87001234567"})
    assert b.json()["is_new_user"] is False  # тот же пользователь


async def test_login_invalid_phone_400(client):
    res = await client.post("/api/auth/login", json={"phone": "1234567890123"})
    assert res.status_code == 400


async def test_login_token_authorizes_me(client):
    res = await client.post("/api/auth/login", json={"phone": "+77001234567"})
    token = res.json()["access_token"]
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["phone"] == "+77001234567"
