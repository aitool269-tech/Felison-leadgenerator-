import io
from unittest.mock import patch

import openpyxl


def maak_xlsx(rijen):
    """rijen: lijst dicts met keys Vergunningnummer/Naam/Rechtsvorm/... Eerste rij = koptekst."""
    wb = openpyxl.Workbook()
    ws = wb.active
    kolommen = ["Vergunningnummer", "Naam", "Rechtsvorm", "KvK-nummer", "Adres",
                "Dienst", "Beperkingen vergunning", "Begindatum vergunning", "Begindatum dienst"]
    ws.append(kolommen)
    for rij in rijen:
        ws.append([rij.get(k) for k in kolommen])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def maak_csv(rijen):
    """rijen: lijst tuples (naam, handelsnaam, plaats)."""
    regels = ["naam;handelsnaam;plaats"] + [";".join(r) for r in rijen]
    return io.BytesIO("\n".join(regels).encode("utf-8-sig"))


def geen_geocode_resultaat(*args, **kwargs):
    class Resp:
        def json(self):
            return {"response": {"docs": []}}
    return Resp()


def test_nieuwe_lead_wordt_geimporteerd_en_gescoord(client):
    xlsx = maak_xlsx([{
        "Vergunningnummer": "AFM-1", "Naam": "Nieuw Kantoor BV", "Rechtsvorm": "B.V.",
        "Dienst": "Adviseren / Bemiddelen", "Adres": "Teststraat 1 1234AB Teststad NL",
    }])
    csv = maak_csv([])
    with patch("app.requests.get", side_effect=geen_geocode_resultaat):
        r = client.post("/api/import",
                         files={"xlsx": ("R0443.xlsx", xlsx,
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                                "register_csv": ("register.csv", csv, "text/csv")})
    assert r.status_code == 200
    data = r.json()
    assert data["nieuw"] == 1
    leads = client.get("/api/leads").json()
    assert leads[0]["vergunningnummer"] == "AFM-1"
    assert leads[0]["klasse"] in ("A", "B", "C")


def test_bestaand_vergunningnummer_wordt_overgeslagen_als_dubbel(client):
    xlsx = maak_xlsx([{"Vergunningnummer": "AFM-2", "Naam": "Kantoor Twee", "Dienst": "Adviseren / Bemiddelen"}])
    csv = maak_csv([])
    with patch("app.requests.get", side_effect=geen_geocode_resultaat):
        client.post("/api/import", files={
            "xlsx": ("R0443.xlsx", maak_xlsx([{"Vergunningnummer": "AFM-2", "Naam": "Kantoor Twee", "Dienst": "Adviseren / Bemiddelen"}]), "application/octet-stream"),
            "register_csv": ("register.csv", maak_csv([]), "text/csv")})
        r = client.post("/api/import", files={
            "xlsx": ("R0443.xlsx", xlsx, "application/octet-stream"),
            "register_csv": ("register.csv", csv, "text/csv")})
    data = r.json()
    assert data["nieuw"] == 0
    assert data["dubbel_overgeslagen"] == 1


def test_afgewezen_lead_wordt_automatisch_heropend_bij_hernieuwde_import(client, con_factory):
    with patch("app.requests.get", side_effect=geen_geocode_resultaat):
        client.post("/api/import", files={
            "xlsx": ("R0443.xlsx", maak_xlsx([{"Vergunningnummer": "AFM-3", "Naam": "Kantoor Drie", "Dienst": "Adviseren / Bemiddelen"}]), "application/octet-stream"),
            "register_csv": ("register.csv", maak_csv([]), "text/csv")})
    con = con_factory()
    con.execute("UPDATE leads SET status='Afgewezen' WHERE vergunningnummer='AFM-3'")
    con.commit(); con.close()
    with patch("app.requests.get", side_effect=geen_geocode_resultaat):
        r = client.post("/api/import", files={
            "xlsx": ("R0443.xlsx", maak_xlsx([{"Vergunningnummer": "AFM-3", "Naam": "Kantoor Drie", "Dienst": "Adviseren / Bemiddelen"}]), "application/octet-stream"),
            "register_csv": ("register.csv", maak_csv([]), "text/csv")})
    data = r.json()
    assert data["heropend"] == 1
    lead = client.get("/api/leads").json()[0]
    assert lead["status"] == "Opnieuw binnen"


def test_register_match_vult_handelsnaam_en_plaats_aan(client):
    xlsx = maak_xlsx([{"Vergunningnummer": "AFM-4", "Naam": "Kantoor Vier", "Dienst": "Adviseren / Bemiddelen"}])
    csv = maak_csv([("Kantoor Vier", "Vier Verzekeringen", "Utrecht")])
    with patch("app.requests.get", side_effect=geen_geocode_resultaat):
        r = client.post("/api/import", files={
            "xlsx": ("R0443.xlsx", xlsx, "application/octet-stream"),
            "register_csv": ("register.csv", csv, "text/csv")})
    assert r.json()["gematcht_met_register"] == 1
    lead = client.get("/api/leads").json()[0]
    assert lead["handelsnamen"] == "Vier Verzekeringen"
    assert lead["plaats"] == "Utrecht"


def test_xlsx_zonder_verplichte_kolommen_geeft_400(client):
    wb = openpyxl.Workbook()
    wb.active.append(["Iets", "Anders"])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    r = client.post("/api/import", files={
        "xlsx": ("R0443.xlsx", buf, "application/octet-stream"),
        "register_csv": ("register.csv", maak_csv([]), "text/csv")})
    assert r.status_code == 400
