from datetime import date, timedelta


def maak_lead(con_factory, **overrides):
    con = con_factory()
    velden = {
        "vergunningnummer": "TEST-001", "naam": "Test Kantoor",
        "status": "Benaderd", "score": 60, "klasse": "B", "score_basis": 60,
        "aangemaakt": (date.today() - timedelta(days=30)).isoformat(),
    }
    velden.update(overrides)
    kolommen = ", ".join(velden.keys())
    plekken = ", ".join("?" for _ in velden)
    lead_id = con.insert_id(f"INSERT INTO leads({kolommen}) VALUES({plekken})", tuple(velden.values()))
    con.commit(); con.close()
    return lead_id


def test_aandacht_signaleert_verlopen_vervolgactie(client, con_factory):
    verlopen = (date.today() - timedelta(days=2)).isoformat()
    maak_lead(con_factory, vervolg_datum=verlopen, status="Geclaimd")
    r = client.get("/api/aandacht").json()
    assert len(r) == 1
    assert "Vervolgactie verlopen" in r[0]["reden"]


def test_aandacht_signaleert_stilgevallen_lead(client, con_factory):
    oud = (date.today() - timedelta(days=40)).isoformat()
    maak_lead(con_factory, aangemaakt=oud, status="Benaderd")
    r = client.get("/api/aandacht").json()
    assert len(r) == 1
    assert "geen update" in r[0]["reden"]


def test_aandacht_negeert_ongeldige_vervolg_datum_zonder_crash(client, con_factory):
    maak_lead(con_factory, vervolg_datum="2024-13-40", aangemaakt=date.today().isoformat(), status="Benaderd")
    r = client.get("/api/aandacht")
    assert r.status_code == 200
    assert r.json() == []


def test_aandacht_negeert_recente_en_afgesloten_leads(client, con_factory):
    maak_lead(con_factory, status="Afgewezen")  # afgesloten: telt nooit mee
    maak_lead(con_factory, aangemaakt=date.today().isoformat(), status="Benaderd", vergunningnummer="X2")  # recent
    r = client.get("/api/aandacht").json()
    assert r == []
