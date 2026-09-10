def _brief_payload(**overrides):
    payload = {
        "audience": "18-30 mobil oyuncular",
        "single_message": "Bu oyun bagimlilik yapiyor",
        "objective": "install",
        "style_id": "energetic-v1",
        "language": "tr",
        "target_frames": 900,
        "fps_num": 30,
        "fps_den": 1,
        "placement_id": "meta-feed-9x16",
        "budget_microusd": 50_000_000,
        "product_name": "Synova",
        "description": "Sirayi hatirlama mekanigine dayali kisa turlu bir hafiza oyunu.",
        "cta": "Simdi indir",
    }
    payload.update(overrides)
    return payload


def test_put_brief_creates_first_revision(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Brief Testi"}).json()

    response = api_client.put(f"/api/v1/projects/{project['id']}/brief", json=_brief_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["revision"] == 1
    assert body["project_id"] == project["id"]
    assert body["budget_microusd"] == 50_000_000


def test_put_brief_twice_creates_second_revision_not_overwrite(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Brief Revizyon Testi"}).json()

    first = api_client.put(
        f"/api/v1/projects/{project['id']}/brief", json=_brief_payload(single_message="ilk mesaj")
    ).json()
    second = api_client.put(
        f"/api/v1/projects/{project['id']}/brief", json=_brief_payload(single_message="ikinci mesaj")
    ).json()

    assert first["revision"] == 1
    assert second["revision"] == 2
    assert first["id"] != second["id"]
    assert second["single_message"] == "ikinci mesaj"


def test_put_brief_for_unknown_project_returns_404(api_client):
    response = api_client.put("/api/v1/projects/does-not-exist/brief", json=_brief_payload())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_blank_audience_and_single_message_get_spec_defaults(api_client):
    """Spec 3.2/4.2: only product_name/description/cta are mandatory on the
    brief screen — every other field, audience and single_message included,
    must fall back to a default rather than 422 the request."""
    project = api_client.post("/api/v1/projects", json={"name": "Varsayilan Testi"}).json()

    response = api_client.put(
        f"/api/v1/projects/{project['id']}/brief",
        json=_brief_payload(audience="", single_message=""),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["audience"]  # non-empty default, not the blank the user left
    assert body["single_message"] == _brief_payload()["description"]


def test_put_brief_missing_mandatory_brand_field_returns_422(api_client):
    project = api_client.post("/api/v1/projects", json={"name": "Zorunlu Alan Testi"}).json()
    payload = _brief_payload()
    del payload["product_name"]

    response = api_client.put(f"/api/v1/projects/{project['id']}/brief", json=payload)
    assert response.status_code == 422


def test_put_brief_upserts_single_brand_profile_row(api_client, db_session):
    from app.models.project import BrandProfile

    project = api_client.post("/api/v1/projects", json={"name": "Marka Profili Testi"}).json()

    api_client.put(
        f"/api/v1/projects/{project['id']}/brief",
        json=_brief_payload(product_name="Synova v1"),
    )
    api_client.put(
        f"/api/v1/projects/{project['id']}/brief",
        json=_brief_payload(product_name="Synova v2"),
    )

    rows = (
        db_session.query(BrandProfile)
        .filter(BrandProfile.project_id == project["id"])
        .all()
    )
    assert len(rows) == 1  # upsert, not a second row per revision
    assert rows[0].product_name == "Synova v2"
