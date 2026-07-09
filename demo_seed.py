"""Demo-omgeving: vult een lege database met fictieve, realistische data.

Actief wanneer DEMO_MODE gezet is (apart Vercel-project). Draait bij elke koude
start; omdat de demo zonder Postgres in /tmp leeft, wordt de data daarmee
vanzelf periodiek teruggezet naar deze nette beginstaat — ideaal voor demonstraties.
Alle kantoornamen zijn verzonnen; adressen zijn alleen stad + coördinaten.
"""
from datetime import date, datetime, timedelta

from database import DB

AMS = [("Patrick", "#5B63C7"), ("Sandra", "#D4537E"), ("Jeroen", "#1D9E75")]

VANDAAG = date.today()


def d(dagen_terug):
    return (VANDAAG - timedelta(days=dagen_terug)).isoformat()


def ts(dagen_terug, uur=10):
    return datetime.combine(VANDAAG - timedelta(days=dagen_terug), datetime.min.time()).replace(hour=uur).isoformat(sep=" ")


# (naam, plaats, provincie, lat, lon, score, klasse, status, am, website, vervolg_datum, vervolg_actie, dagen_geleden_binnen)
LEADS = [
    ("Waterland Assurantiën B.V.", "Amsterdam", "Noord-Holland", 52.37, 4.90, 90, "A", "Aanstelling", "Patrick", "https://voorbeeld.nl", None, None, 33),
    ("Maasstad Adviesgroep B.V.", "Rotterdam", "Zuid-Holland", 51.92, 4.48, 88, "A", "Aanstelling", "Sandra", "https://voorbeeld.nl", None, None, 40),
    ("Domstad Inkomensadvies B.V.", "Utrecht", "Utrecht", 52.09, 5.12, 92, "A", "In gesprek", "Patrick", "https://voorbeeld.nl", d(-3), "offerte bespreken", 21),
    ("IJsselland Verzekeringen B.V.", "Zwolle", "Overijssel", 52.51, 6.09, 85, "A", "Benaderd", "Jeroen", "https://voorbeeld.nl", d(1), "terugbellen na vakantie", 18),
    ("Lichtstad Financieel Advies", "Eindhoven", "Noord-Brabant", 51.44, 5.48, 80, "A", "Benaderd", "Sandra", None, d(0), "offerte nasturen", 15),
    ("Martini Assurantiekantoor B.V.", "Groningen", "Groningen", 53.22, 6.57, 75, "A", "Geclaimd", "Patrick", None, d(-7), "kennismaking plannen", 12),
    ("Rijnpoort Adviseurs B.V.", "Arnhem", "Gelderland", 51.98, 5.91, 72, "A", "Geclaimd", "Jeroen", None, None, None, 9),
    ("Baroniestad Verzekeringen", "Breda", "Noord-Brabant", 51.59, 4.78, 65, "B", "Opnieuw binnen", "Sandra", None, None, None, 65),
    ("Friesland Inkomensplanners", "Leeuwarden", "Fryslân", 53.20, 5.80, 78, "A", "Afgewezen", "Jeroen", "https://voorbeeld.nl", None, None, 28),
    ("Mosae Advies & Bemiddeling B.V.", "Maastricht", "Limburg", 50.85, 5.69, 82, "A", "Nieuw", None, None, None, None, 5),
    ("Zeelandia Assurantiën B.V.", "Middelburg", "Zeeland", 51.50, 3.61, 68, "B", "Nieuw", None, None, None, None, 4),
    ("Polderstad Risicoadvies", "Almere", "Flevoland", 52.37, 5.22, 55, "B", "Nieuw", None, None, None, None, 3),
]

# (leadnr, soort, label/status, notitie, am, dagen_terug)
ACTIVITEIT = [
    (1, "status", "Geclaimd", None, "Patrick", 30),
    (1, "contact", "Gebeld", "Prettig eerste gesprek, staat open voor samenwerking.", "Patrick", 28),
    (1, "status", "Benaderd", None, "Patrick", 28),
    (1, "status", "In gesprek", "Voorstel doorgenomen op kantoor.", "Patrick", 18),
    (1, "status", "Aanstelling", "Aanstelling rond! Papierwerk getekend.", "Patrick", 8),
    (2, "status", "Geclaimd", None, "Sandra", 36),
    (2, "contact", "Gemaild", "Introductiemail met brochure gestuurd.", "Sandra", 35),
    (2, "status", "Benaderd", None, "Sandra", 33),
    (2, "status", "In gesprek", None, "Sandra", 24),
    (2, "status", "Aanstelling", "Getekend na tweede gesprek.", "Sandra", 12),
    (3, "status", "Geclaimd", None, "Patrick", 19),
    (3, "contact", "Gebeld", "Eerste keer niet bereikt, voicemail ingesproken.", "Patrick", 17),
    (3, "contact", "Gebeld", "Goed gesprek; wil offerte zien.", "Patrick", 14),
    (3, "status", "Benaderd", None, "Patrick", 14),
    (3, "status", "In gesprek", "Offerte verstuurd, volgende week bespreken.", "Patrick", 6),
    (4, "status", "Geclaimd", None, "Jeroen", 16),
    (4, "contact", "Gesproken", "Gesproken op vakbeurs, positief.", "Jeroen", 11),
    (4, "status", "Benaderd", None, "Jeroen", 11),
    (5, "status", "Geclaimd", None, "Sandra", 13),
    (5, "contact", "Gebeld", "Wil eerst intern overleggen.", "Sandra", 9),
    (5, "status", "Benaderd", None, "Sandra", 9),
    (6, "status", "Geclaimd", None, "Patrick", 10),
    (7, "status", "Geclaimd", None, "Jeroen", 7),
    (8, "status", "Geclaimd", None, "Sandra", 60),
    (8, "status", "Geen interesse", "Zit vast aan huidige volmacht tot eind dit jaar.", "Sandra", 50),
    (8, "status", "Opnieuw binnen", "Automatisch heropend: kantoor kwam opnieuw voor in het AFM-bestand", None, 2),
    (9, "status", "Geclaimd", None, "Jeroen", 26),
    (9, "contact", "Gebeld", "Geen interesse, tevreden bij huidige partij.", "Jeroen", 22),
    (9, "status", "Afgewezen", "Recent al aangesloten bij concurrent.", "Jeroen", 22),
]


def seed_indien_leeg():
    con = DB()
    if con.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"] > 0:
        con.close()
        return
    for naam, kleur in AMS:
        con.upsert_am(naam, kleur)
    import_id = con.insert_id("INSERT INTO imports(bestanden, nieuw, dubbel, gematcht) VALUES(?,?,?,?)",
                              ("DEMO — Nieuwe inkomensvergunningen (R0443).xlsx + register.csv", len(LEADS), 0, len(LEADS)))
    for i, (naam, plaats, prov, lat, lon, score, klasse, status, am, web, vdatum, vactie, dagen) in enumerate(LEADS, 1):
        con.execute("""INSERT INTO leads(vergunningnummer, naam, rechtsvorm, kvk, plaats, provincie, lat, lon,
            dienst, begindatum_vergunning, begindatum_dienst, score, score_basis, klasse, score_uitleg,
            website, status, am, vervolg_datum, vervolg_actie, import_id, aangemaakt)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"90{i:06d}", naam, "Besloten Vennootschap" if "B.V." in naam else None, f"9{i:07d}",
             plaats, prov, lat, lon, "Adviseren / Bemiddelen", d(dagen), d(dagen),
             score, score, klasse, "demo-lead: fictieve scoreopbouw",
             web, status, am, vdatum, vactie, import_id, ts(dagen)))
        con.execute("INSERT INTO lead_historie(vergunningnummer, naam, import_id, ts) VALUES(?,?,?,?)",
                    (f"90{i:06d}", naam, import_id, ts(dagen)))
        if status == "Opnieuw binnen":  # tweede binnenkomst voor de ×2-markering
            con.execute("INSERT INTO lead_historie(vergunningnummer, naam, import_id, ts) VALUES(?,?,?,?)",
                        (f"90{i:06d}", naam, import_id, ts(2)))
    for leadnr, soort, label, notitie, am, dagen in ACTIVITEIT:
        if soort == "status":
            con.execute("INSERT INTO status_log(lead_id, status, am, notitie, ts) VALUES(?,?,?,?,?)",
                        (leadnr, label, am, notitie, ts(dagen, 14)))
        else:
            con.execute("INSERT INTO contactmomenten(lead_id, type, notitie, am, ts) VALUES(?,?,?,?,?)",
                        (leadnr, label, notitie, am, ts(dagen, 11)))
    con.commit()
    con.close()
