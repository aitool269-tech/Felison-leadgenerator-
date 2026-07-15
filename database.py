"""Opslaglaag: SQLite lokaal, Postgres (DATABASE_URL/POSTGRES_URL) op Vercel.

Zonder Postgres op Vercel valt de app terug op /tmp (niet-permanent, demo-modus);
PERSISTENT geeft aan of data bewaard blijft.
"""
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, unquote

PG_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
IS_VERCEL = bool(os.environ.get("VERCEL"))
PERSISTENT = bool(PG_URL) or not IS_VERCEL
SQLITE_PATH = Path("/tmp/leads.db") if IS_VERCEL else Path(__file__).parent / "leads.db"

# Statements gescheiden door ';;' zodat ze per stuk uitgevoerd kunnen worden.
DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS leads(
    id INTEGER PRIMARY KEY,
    vergunningnummer TEXT UNIQUE NOT NULL,
    naam TEXT NOT NULL,
    handelsnamen TEXT, rechtsvorm TEXT, kvk TEXT,
    adres TEXT, postcode TEXT, plaats TEXT, provincie TEXT,
    lat REAL, lon REAL,
    dienst TEXT, beperkingen TEXT,
    begindatum_vergunning TEXT, begindatum_dienst TEXT,
    score INTEGER, klasse TEXT, score_uitleg TEXT,
    score_basis INTEGER, website_score INTEGER, website_uitleg TEXT,
    website TEXT,
    telefoon TEXT, email TEXT, contactpersoon TEXT,
    vervolg_datum TEXT, vervolg_actie TEXT,
    presentje_datum TEXT, presentje_type TEXT,
    relatie_match TEXT, relatie_naam TEXT, relatie_bron TEXT,
    status TEXT DEFAULT 'Nieuw',
    am TEXT,
    import_id INTEGER,
    aangemaakt TEXT DEFAULT (datetime('now'))
);;
CREATE TABLE IF NOT EXISTS presentje_types(naam TEXT PRIMARY KEY);;
CREATE TABLE IF NOT EXISTS instellingen(sleutel TEXT PRIMARY KEY, waarde TEXT);;
CREATE TABLE IF NOT EXISTS relaties(
    id INTEGER PRIMARY KEY,
    naam TEXT NOT NULL,
    naam_norm TEXT,
    bron TEXT,
    ts TEXT DEFAULT (datetime('now')),
    UNIQUE(naam_norm, bron)
);;
CREATE TABLE IF NOT EXISTS feedback(
    id INTEGER PRIMARY KEY,
    naam TEXT, tekst TEXT, scherm TEXT,
    ts TEXT DEFAULT (datetime('now'))
);;
CREATE TABLE IF NOT EXISTS status_log(
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    status TEXT, am TEXT, notitie TEXT,
    ts TEXT DEFAULT (datetime('now'))
);;
CREATE TABLE IF NOT EXISTS ams(naam TEXT PRIMARY KEY, kleur TEXT, email TEXT);;
CREATE TABLE IF NOT EXISTS imports(
    id INTEGER PRIMARY KEY,
    ts TEXT DEFAULT (datetime('now')),
    bestanden TEXT,
    nieuw INTEGER, dubbel INTEGER, gematcht INTEGER
);;
CREATE TABLE IF NOT EXISTS lead_historie(
    id INTEGER PRIMARY KEY,
    vergunningnummer TEXT NOT NULL,
    naam TEXT,
    import_id INTEGER,
    ts TEXT DEFAULT (datetime('now'))
);;
CREATE TABLE IF NOT EXISTS contactmomenten(
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    type TEXT, notitie TEXT, am TEXT,
    ts TEXT DEFAULT (datetime('now'))
)
"""

DDL_PG = """
CREATE TABLE IF NOT EXISTS leads(
    id SERIAL PRIMARY KEY,
    vergunningnummer TEXT UNIQUE NOT NULL,
    naam TEXT NOT NULL,
    handelsnamen TEXT, rechtsvorm TEXT, kvk TEXT,
    adres TEXT, postcode TEXT, plaats TEXT, provincie TEXT,
    lat DOUBLE PRECISION, lon DOUBLE PRECISION,
    dienst TEXT, beperkingen TEXT,
    begindatum_vergunning TEXT, begindatum_dienst TEXT,
    score INTEGER, klasse TEXT, score_uitleg TEXT,
    score_basis INTEGER, website_score INTEGER, website_uitleg TEXT,
    website TEXT,
    telefoon TEXT, email TEXT, contactpersoon TEXT,
    vervolg_datum TEXT, vervolg_actie TEXT,
    presentje_datum TEXT, presentje_type TEXT,
    relatie_match TEXT, relatie_naam TEXT, relatie_bron TEXT,
    status TEXT DEFAULT 'Nieuw',
    am TEXT,
    import_id INTEGER,
    aangemaakt TIMESTAMP DEFAULT now()
);;
CREATE TABLE IF NOT EXISTS presentje_types(naam TEXT PRIMARY KEY);;
CREATE TABLE IF NOT EXISTS instellingen(sleutel TEXT PRIMARY KEY, waarde TEXT);;
CREATE TABLE IF NOT EXISTS relaties(
    id SERIAL PRIMARY KEY,
    naam TEXT NOT NULL,
    naam_norm TEXT,
    bron TEXT,
    ts TIMESTAMP DEFAULT now(),
    UNIQUE(naam_norm, bron)
);;
CREATE TABLE IF NOT EXISTS feedback(
    id SERIAL PRIMARY KEY,
    naam TEXT, tekst TEXT, scherm TEXT,
    ts TIMESTAMP DEFAULT now()
);;
CREATE TABLE IF NOT EXISTS status_log(
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    status TEXT, am TEXT, notitie TEXT,
    ts TIMESTAMP DEFAULT now()
);;
CREATE TABLE IF NOT EXISTS ams(naam TEXT PRIMARY KEY, kleur TEXT, email TEXT);;
CREATE TABLE IF NOT EXISTS imports(
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP DEFAULT now(),
    bestanden TEXT,
    nieuw INTEGER, dubbel INTEGER, gematcht INTEGER
);;
CREATE TABLE IF NOT EXISTS lead_historie(
    id SERIAL PRIMARY KEY,
    vergunningnummer TEXT NOT NULL,
    naam TEXT,
    import_id INTEGER,
    ts TIMESTAMP DEFAULT now()
);;
CREATE TABLE IF NOT EXISTS contactmomenten(
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    type TEXT, notitie TEXT, am TEXT,
    ts TIMESTAMP DEFAULT now()
)
"""


class Result:
    """Uniforme rij-toegang: itereren en fetchone() geven dicts."""

    def __init__(self, cur):
        self.cur = cur
        self.cols = [d[0] for d in cur.description] if cur.description else []

    def fetchone(self):
        r = self.cur.fetchone()
        return dict(zip(self.cols, r)) if r else None

    def __iter__(self):
        for r in self.cur.fetchall():
            yield dict(zip(self.cols, r))


class DB:
    def __init__(self):
        if PG_URL:
            import ssl
            import pg8000.dbapi
            u = urlparse(PG_URL)
            self.con = pg8000.dbapi.connect(
                user=unquote(u.username or ""),
                password=unquote(u.password or ""),
                host=u.hostname,
                port=u.port or 5432,
                database=(u.path or "/postgres").lstrip("/") or "postgres",
                ssl_context=ssl.create_default_context(),
            )
            self.pg = True
        else:
            self.con = sqlite3.connect(SQLITE_PATH)
            self.pg = False

    def execute(self, sql, params=()):
        cur = self.con.cursor()
        cur.execute(sql.replace("?", "%s") if self.pg else sql, tuple(params))
        return Result(cur)

    def insert_id(self, sql, params=()):
        """INSERT uitvoeren en het nieuwe id teruggeven (RETURNING op pg, lastrowid op sqlite)."""
        if self.pg:
            cur = self.con.cursor()
            cur.execute(sql.replace("?", "%s") + " RETURNING id", tuple(params))
            return cur.fetchone()[0]
        cur = self.con.cursor()
        cur.execute(sql, tuple(params))
        return cur.lastrowid

    def upsert_am(self, naam, kleur, email=None):
        if self.pg:
            self.execute(
                "INSERT INTO ams(naam,kleur,email) VALUES(?,?,?) "
                "ON CONFLICT(naam) DO UPDATE SET kleur=EXCLUDED.kleur, email=EXCLUDED.email",
                (naam, kleur, email))
        else:
            self.execute("INSERT OR REPLACE INTO ams(naam,kleur,email) VALUES(?,?,?)", (naam, kleur, email))

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()


MIGRATIES = [
    "ALTER TABLE leads ADD COLUMN score_basis INTEGER",
    "ALTER TABLE leads ADD COLUMN website_score INTEGER",
    "ALTER TABLE leads ADD COLUMN website_uitleg TEXT",
    "ALTER TABLE leads ADD COLUMN telefoon TEXT",
    "ALTER TABLE leads ADD COLUMN email TEXT",
    "ALTER TABLE leads ADD COLUMN contactpersoon TEXT",
    "ALTER TABLE leads ADD COLUMN vervolg_datum TEXT",
    "ALTER TABLE leads ADD COLUMN vervolg_actie TEXT",
    "ALTER TABLE leads ADD COLUMN presentje_datum TEXT",
    "ALTER TABLE leads ADD COLUMN presentje_type TEXT",
    "ALTER TABLE leads ADD COLUMN relatie_match TEXT",
    "ALTER TABLE leads ADD COLUMN relatie_naam TEXT",
    "ALTER TABLE leads ADD COLUMN relatie_bron TEXT",
    "ALTER TABLE ams ADD COLUMN email TEXT",
    "ALTER TABLE relaties ADD COLUMN bron TEXT",
    "ALTER TABLE relaties DROP CONSTRAINT relaties_naam_norm_key",
]


def init_db():
    d = DB()
    for stmt in (DDL_PG if d.pg else DDL_SQLITE).split(";;"):
        if stmt.strip():
            d.execute(stmt)
    d.commit()
    for stmt in MIGRATIES:
        try:
            d.execute(stmt)
            d.commit()
        except Exception:
            try:
                d.con.rollback()
            except Exception:
                pass
    d.execute("UPDATE leads SET score_basis=score WHERE score_basis IS NULL")
    # Backfill: bestaande leads die nog geen historieregel hebben, krijgen hun
    # oorspronkelijke binnenkomst (import + datum) als eerste historievermelding.
    d.execute("""INSERT INTO lead_historie(vergunningnummer, naam, import_id, ts)
                 SELECT vergunningnummer, naam, import_id, aangemaakt FROM leads
                 WHERE vergunningnummer NOT IN (SELECT vergunningnummer FROM lead_historie)""")
    d.commit()
    d.close()
