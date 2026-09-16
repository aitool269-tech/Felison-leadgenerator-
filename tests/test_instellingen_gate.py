def test_zonder_instellingen_wachtwoord_is_alles_open(client):
    # Geen instellingen_wachtwoord gezet (verse testdatabase) -> niets is gated.
    r = client.get("/api/ams")
    assert r.status_code == 200

    r = client.post("/api/ams", json={"naam": "Anna"})
    assert r.status_code == 200


def test_met_instellingen_wachtwoord_blijft_lezen_open_maar_schrijven_niet(client, con_factory):
    con = con_factory()
    con.execute("INSERT INTO instellingen(sleutel, waarde) VALUES(?,?)",
                ("instellingen_wachtwoord", "geheim123"))
    con.commit()
    con.close()

    # GET /api/ams blijft open voor iedereen, ook zonder header — dit is exact
    # de invariant die tijdens de ontwikkeling van de gate ooit brak.
    r = client.get("/api/ams")
    assert r.status_code == 200

    r = client.post("/api/ams", json={"naam": "Bram"})
    assert r.status_code == 401

    r = client.post("/api/ams", json={"naam": "Bram"},
                     headers={"X-Instellingen-Code": "geheim123"})
    assert r.status_code == 200

    # POST /api/feedback is de globale feedbackknop en blijft open.
    r = client.post("/api/feedback", json={"tekst": "Werkt goed"})
    assert r.status_code == 200

    # GET /api/feedback (de lijst in Instellingen) is wel gated.
    r = client.get("/api/feedback")
    assert r.status_code == 401


def test_relaties_status_blijft_open_maar_import_niet(client, con_factory):
    # Regressie: het Rapport-tabblad roept GET /api/relaties/status aan zonder
    # ooit het instellingen-wachtwoord op te vragen. Stond dit endpoint achter
    # de volledige gate, dan bleef het Rapport-tabblad leeg zodra een
    # instellingen_wachtwoord was ingesteld (de fetch faalde stil op een 401).
    con = con_factory()
    con.execute("INSERT INTO instellingen(sleutel, waarde) VALUES(?,?)",
                ("instellingen_wachtwoord", "geheim123"))
    con.commit()
    con.close()

    r = client.get("/api/relaties/status")
    assert r.status_code == 200

    r = client.post("/api/relaties/import?bron=Felison",
                     files={"bestand": ("relaties.csv", b"Tussenpersoon\nTest\n", "text/csv")})
    assert r.status_code == 401

    r = client.post("/api/relaties/import?bron=Felison",
                     files={"bestand": ("relaties.csv", b"Tussenpersoon\nTest\n", "text/csv")},
                     headers={"X-Instellingen-Code": "geheim123"})
    assert r.status_code == 200
