def maak_lead(con_factory, **overrides):
    con = con_factory()
    velden = {
        "vergunningnummer": "TEST-001",
        "naam": "Test Assurantiën",
        "status": "Nieuw",
        "am": None,
        "score": 60, "klasse": "B", "score_basis": 60,
        "aangemaakt": "2025-01-01",
    }
    velden.update(overrides)
    kolommen = ", ".join(velden.keys())
    plekken = ", ".join("?" for _ in velden)
    lead_id = con.insert_id(
        f"INSERT INTO leads({kolommen}) VALUES({plekken})", tuple(velden.values()))
    con.commit()
    con.close()
    return lead_id


def test_conversie_verdeling_telt_status_klasse_en_am(client, con_factory):
    maak_lead(con_factory, naam="A", status="Nieuw", klasse="A", am=None)
    maak_lead(con_factory, naam="B", status="Aanstelling", klasse="B", am="Anna", vergunningnummer="X2")
    r = client.get("/api/conversie").json()
    assert r["verdeling"]["status"]["Nieuw"] == 1
    assert r["verdeling"]["status"]["Aanstelling"] == 1
    assert r["verdeling"]["klasse"]["A"] == 1
    assert r["verdeling"]["am"]["Niet geclaimd"] == 1
    assert r["verdeling"]["am"]["Anna"] == 1


def test_conversie_provincies_telt_leads_en_aanstellingen(client, con_factory):
    maak_lead(con_factory, naam="A", provincie="Utrecht", status="Aanstelling", vergunningnummer="X1")
    maak_lead(con_factory, naam="B", provincie="Utrecht", status="Nieuw", vergunningnummer="X2")
    maak_lead(con_factory, naam="C", provincie=None, status="Nieuw", vergunningnummer="X3")
    r = client.get("/api/conversie").json()
    utrecht = next(p for p in r["provincies"] if p["provincie"] == "Utrecht")
    assert utrecht["leads"] == 2
    assert utrecht["aanstelling"] == 1
    assert utrecht["conversie_pct"] == 50.0
    onbekend = next(p for p in r["provincies"] if p["provincie"] == "Onbekend")
    assert onbekend["leads"] == 1


def test_conversie_periodefilter_sluit_leads_buiten_bereik_uit(client, con_factory):
    maak_lead(con_factory, naam="Oud", vergunningnummer="X1", aangemaakt="2024-01-15")
    maak_lead(con_factory, naam="Nieuw", vergunningnummer="X2", aangemaakt="2025-06-15")
    r = client.get("/api/conversie", params={"vanaf": "2025-01-01"}).json()
    assert r["verdeling"]["status"].get("Nieuw", 0) == 1  # alleen de lead uit 2025 telt mee
    totaal = sum(r["verdeling"]["status"].values())
    assert totaal == 1


def test_conversie_periodefilter_tot_sluit_leads_na_bereik_uit(client, con_factory):
    maak_lead(con_factory, naam="Voor", vergunningnummer="X1", aangemaakt="2025-01-15")
    maak_lead(con_factory, naam="Na", vergunningnummer="X2", aangemaakt="2025-06-15")
    r = client.get("/api/conversie", params={"tot": "2025-02-01"}).json()
    assert sum(r["verdeling"]["status"].values()) == 1  # alleen de lead vóór 2025-02-01 telt mee


def test_conversie_periodefilter_tot_is_inclusief_de_einddatum(client, con_factory):
    maak_lead(con_factory, naam="OpGrens", vergunningnummer="X1", aangemaakt="2025-02-01 10:00:00")
    r = client.get("/api/conversie", params={"tot": "2025-02-01"}).json()
    assert sum(r["verdeling"]["status"].values()) == 1  # 23:59:59 wordt aan 'tot' toegevoegd


def test_conversie_periodefilter_vanaf_en_tot_combineren(client, con_factory):
    maak_lead(con_factory, naam="Voor", vergunningnummer="X1", aangemaakt="2024-12-01")
    maak_lead(con_factory, naam="In", vergunningnummer="X2", aangemaakt="2025-01-15")
    maak_lead(con_factory, naam="Na", vergunningnummer="X3", aangemaakt="2025-03-01")
    r = client.get("/api/conversie", params={"vanaf": "2025-01-01", "tot": "2025-02-01"}).json()
    assert sum(r["verdeling"]["status"].values()) == 1  # alleen "In" valt binnen het bereik
