def maak_lead(con_factory, **overrides):
    con = con_factory()
    velden = {
        "vergunningnummer": "TEST-001",
        "naam": "Test Assurantiën",
        "status": "Nieuw",
        "am": None,
        "score": 60, "klasse": "B", "score_basis": 60,
    }
    velden.update(overrides)
    kolommen = ", ".join(velden.keys())
    plekken = ", ".join("?" for _ in velden)
    lead_id = con.insert_id(
        f"INSERT INTO leads({kolommen}) VALUES({plekken})", tuple(velden.values()))
    con.commit()
    con.close()
    return lead_id


def test_claim_zet_am_en_status_geclaimd_bij_status_nieuw(client, con_factory):
    lead_id = maak_lead(con_factory, status="Nieuw")
    r = client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    assert r.status_code == 200
    lead = client.get("/api/leads").json()[0]
    assert lead["am"] == "Anna"
    assert lead["status"] == "Geclaimd"


def test_claim_laat_afwijkende_status_ongemoeid(client, con_factory):
    lead_id = maak_lead(con_factory, status="Opnieuw binnen")
    client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    lead = client.get("/api/leads").json()[0]
    assert lead["status"] == "Opnieuw binnen"


def test_claim_door_dezelfde_am_is_idempotent(client, con_factory):
    lead_id = maak_lead(con_factory, status="Nieuw")
    client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    r = client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    assert r.status_code == 200


def test_claim_door_andere_am_geeft_409(client, con_factory):
    lead_id = maak_lead(con_factory, status="Nieuw")
    client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    r = client.post(f"/api/leads/{lead_id}/claim", json={"am": "Bram"})
    assert r.status_code == 409


def test_claim_onbekende_lead_geeft_404(client):
    r = client.post("/api/leads/99999/claim", json={"am": "Anna"})
    assert r.status_code == 404


def test_vrijgeven_zet_lead_terug_naar_nieuw(client, con_factory):
    lead_id = maak_lead(con_factory, status="Geclaimd", am="Anna")
    r = client.post(f"/api/leads/{lead_id}/vrijgeven")
    assert r.status_code == 200
    lead = client.get("/api/leads").json()[0]
    assert lead["am"] is None
    assert lead["status"] == "Nieuw"


def test_vrijgeven_onbekende_lead_geeft_404(client):
    r = client.post("/api/leads/99999/vrijgeven")
    assert r.status_code == 404


def test_status_ongeldige_status_geeft_400(client, con_factory):
    lead_id = maak_lead(con_factory)
    r = client.post(f"/api/leads/{lead_id}/status", json={"status": "Onbestaand"})
    assert r.status_code == 400


def test_status_onbekende_lead_geeft_404(client):
    r = client.post("/api/leads/99999/status", json={"status": "Benaderd"})
    assert r.status_code == 404


def test_status_geldige_overgang_wordt_opgeslagen(client, con_factory):
    lead_id = maak_lead(con_factory, status="Geclaimd")
    r = client.post(f"/api/leads/{lead_id}/status", json={"status": "Benaderd", "am": "Anna"})
    assert r.status_code == 200
    lead = client.get("/api/leads").json()[0]
    assert lead["status"] == "Benaderd"


def test_status_wijziging_wordt_altijd_gelogd(client, con_factory):
    lead_id = maak_lead(con_factory, status="Nieuw")
    client.post(f"/api/leads/{lead_id}/status", json={"status": "Benaderd"})
    con = con_factory()
    logs = list(con.execute("SELECT * FROM status_log WHERE lead_id=?", (lead_id,)))
    con.close()
    assert any(l["status"] == "Benaderd" for l in logs)
