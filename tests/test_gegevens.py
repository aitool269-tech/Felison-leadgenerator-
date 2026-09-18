def maak_lead(con_factory, **overrides):
    con = con_factory()
    velden = {
        "vergunningnummer": "TEST-001", "naam": "Test Kantoor",
        "status": "Nieuw", "score": 60, "klasse": "B", "score_basis": 60,
    }
    velden.update(overrides)
    kolommen = ", ".join(velden.keys())
    plekken = ", ".join("?" for _ in velden)
    lead_id = con.insert_id(f"INSERT INTO leads({kolommen}) VALUES({plekken})", tuple(velden.values()))
    con.commit(); con.close()
    return lead_id


def test_gegevens_slaat_functie_contactpersoon_op(client, con_factory):
    lead_id = maak_lead(con_factory)
    r = client.post(f"/api/leads/{lead_id}/gegevens", json={
        "contactpersoon": "J. Jansen", "contactpersoon_functie": "Directeur", "telefoon": "0612345678"})
    assert r.status_code == 200
    lead = client.get("/api/leads").json()[0]
    assert lead["contactpersoon"] == "J. Jansen"
    assert lead["contactpersoon_functie"] == "Directeur"


def test_gegevens_functie_mag_leeg_blijven(client, con_factory):
    lead_id = maak_lead(con_factory)
    r = client.post(f"/api/leads/{lead_id}/gegevens", json={"contactpersoon": "J. Jansen"})
    assert r.status_code == 200
    lead = client.get("/api/leads").json()[0]
    assert lead["contactpersoon_functie"] is None


def test_gegevens_slaat_overvoerpotentie_op(client, con_factory):
    lead_id = maak_lead(con_factory)
    r = client.post(f"/api/leads/{lead_id}/gegevens", json={
        "overvoerpotentie": "Ja", "huidige_aanbieder": "Provinciaal", "overvoerpotentie_premie": 1250.5})
    assert r.status_code == 200
    lead = client.get("/api/leads").json()[0]
    assert lead["overvoerpotentie"] == "Ja"
    assert lead["huidige_aanbieder"] == "Provinciaal"
    assert lead["overvoerpotentie_premie"] == 1250.5


def test_gegevens_overvoerpotentie_premie_mag_nul_zijn(client, con_factory):
    lead_id = maak_lead(con_factory)
    r = client.post(f"/api/leads/{lead_id}/gegevens", json={"overvoerpotentie_premie": 0})
    assert r.status_code == 200
    lead = client.get("/api/leads").json()[0]
    assert lead["overvoerpotentie_premie"] == 0
