import io


def maak_relatie_csv(regels):
    """regels: lijst rijen (lijst kolomwaarden). Eerste regel = koptekst."""
    tekst = "\n".join(";".join(r) for r in regels)
    return io.BytesIO(tekst.encode("utf-8-sig"))


def maak_lead(con_factory, **overrides):
    con = con_factory()
    velden = {
        "vergunningnummer": "TEST-001",
        "naam": "Test Kantoor B.V.",
        "status": "Nieuw",
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


def test_relaties_import_herkent_tussenpersoon_kolom_en_negeert_overige_kolommen(client, con_factory):
    lead_id = maak_lead(con_factory, naam="Test Kantoor B.V.")
    csv = maak_relatie_csv([
        ["TP ID", "Tussenpersoon", "Accountmanager"],
        ["12345", "Test Kantoor B.V.", "Anna"],
    ])
    r = client.post("/api/relaties/import?bron=Felison",
                     files={"bestand": ("relaties.csv", csv, "text/csv")})
    assert r.status_code == 200
    assert r.json()["relaties"] == 1
    assert r.json()["mogelijke_matches"] == 1

    con = con_factory()
    rel = con.execute("SELECT naam FROM relaties").fetchone()
    con.close()
    # De naam moet uit de 'Tussenpersoon'-kolom komen, niet uit 'TP ID' of 'Accountmanager'.
    assert rel["naam"] == "Test Kantoor B.V."

    lead = client.get("/api/leads").json()[0]
    assert lead["id"] == lead_id
    assert lead["relatie_match"] == "mogelijk"


def test_relaties_status_telt_uitkomsten_per_soort(client, con_factory):
    maak_lead(con_factory, naam="A", relatie_match="mogelijk", vergunningnummer="X1")
    maak_lead(con_factory, naam="B", relatie_match="bevestigd", vergunningnummer="X2")
    maak_lead(con_factory, naam="C", relatie_match="geen", vergunningnummer="X3")
    maak_lead(con_factory, naam="D", vergunningnummer="X4")  # relatie_match=NULL, telt nergens mee
    r = client.get("/api/relaties/status").json()
    assert r["per_uitkomst"] == {"mogelijk": 1, "bevestigd": 1, "geen": 1}
    assert r["te_controleren"] == 1
