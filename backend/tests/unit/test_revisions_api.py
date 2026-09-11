def test_create_variation_without_api_key_is_blocked(api_client, monkeypatch):
    import app.api.revisions as revisions_api

    monkeypatch.setattr(revisions_api.credentials_service, "get_credential_value", lambda p: None)
    project = api_client.post("/api/v1/projects", json={"name": "Varyasyon Anahtarsiz"}).json()

    response = api_client.post(
        f"/api/v1/projects/{project['id']}/revisions/does-not-exist/variation",
        json={"shot_instructions": {"shot-1": "x"}},
    )
    # No OpenRouter key configured in the test environment -> blocked before
    # the (nonexistent) revision is even looked up.
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "blocked"
