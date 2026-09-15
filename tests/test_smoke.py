def test_lege_database_geeft_lege_leadlijst(client):
    r = client.get("/api/leads")
    assert r.status_code == 200
    assert r.json() == []


def test_geen_toegangscode_nodig_zonder_access_code_env(client):
    r = client.get("/api/instellingen")
    assert r.status_code == 200
