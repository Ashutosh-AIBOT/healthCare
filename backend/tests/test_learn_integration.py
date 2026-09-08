from tests.helpers_auth import register_verified


async def test_learn_categories_order_and_kinds(client):
    login = await register_verified(client, email="learn-cat@example.com", handle="learn_cat", full_name="Learn")
    token = login.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    food = await client.get("/api/v1/learn/categories?kind=food", headers=h)
    assert food.status_code == 200
    slugs = [c["slug"] for c in food.json()]
    assert slugs == sorted(slugs, key=lambda _: food.json()[slugs.index(_)]["sort_order"])

    all_cats = await client.get("/api/v1/learn/categories", headers=h)
    assert all_cats.status_code == 200
    kinds = {c["kind"] for c in all_cats.json()}
    assert "food" in kinds and "test_info" in kinds


async def test_learn_items_lookup_and_fasting_filter(client):
    login = await register_verified(client, email="learn-items@example.com", handle="learn_items", full_name="Learn")
    token = login.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    cats = await client.get("/api/v1/learn/categories?kind=food", headers=h)
    cat_slug = cats.json()[0]["slug"]
    items = await client.get(f"/api/v1/learn/categories/{cat_slug}/items", headers=h)
    assert items.status_code == 200
    assert len(items.json()) >= 1
    first_slug = items.json()[0]["slug"]
    one = await client.get(f"/api/v1/learn/items/{first_slug}", headers=h)
    assert one.status_code == 200
    assert one.json()["slug"] == first_slug

    fasting = await client.get("/api/v1/learn/tests?fasting=true", headers=h)
    assert fasting.status_code == 200
    assert all(t["fasting_required"] is True for t in fasting.json())
    non = await client.get("/api/v1/learn/tests?fasting=false", headers=h)
    assert non.status_code == 200
    assert all(t["fasting_required"] is False for t in non.json())


async def test_learn_body_parts_top_to_bottom(client):
    login = await register_verified(client, email="learn-body@example.com", handle="learn_body", full_name="Learn")
    token = login.json()["tokens"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    parts = await client.get("/api/v1/learn/body-parts", headers=h)
    assert parts.status_code == 200
    orders = [p["order_index"] for p in parts.json()]
    assert orders == sorted(orders)
    assert parts.json()[0]["slug"] == "head-brain"
    assert parts.json()[-1]["slug"] == "legs-feet"

    first_part = parts.json()[0]["slug"]
    tests = await client.get(f"/api/v1/learn/body-parts/{first_part}/tests", headers=h)
    assert tests.status_code == 200


async def test_learn_requires_auth(client):
    no = await client.get("/api/v1/learn/categories")
    assert no.status_code == 401
