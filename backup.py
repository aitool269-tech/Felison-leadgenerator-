"""Volledige back-up van alle tabellen, en het wegschrijven ervan naar GitHub.

Waarom één rollend bestand in plaats van één bestand per dag: Git bewaart zelf
elke versie (en slaat alleen de verschillen op). Eén bestand per dag zou elke
dag een volledige kopie zijn — bij duizenden leads loopt dat in de gigabytes.
Nu blijft de repo klein en is elke dag terug te halen via de bestandshistorie.
"""
import base64
import json
import os
from datetime import date, datetime

import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
BACKUP_REPO = os.environ.get("BACKUP_REPO")  # bijv. "aitool269-tech/Felison-leadgenerator-backups"
BACKUP_PAD = os.environ.get("BACKUP_PAD", "backup/leadgenerator-backup.json")

# Alle tabellen die samen de volledige staat van de app vormen.
TABELLEN = ["leads", "status_log", "contactmomenten", "lead_historie", "ams",
            "relaties", "instellingen", "presentje_types", "imports", "feedback"]


def backup_actief():
    return bool(GITHUB_TOKEN and BACKUP_REPO)


def _json_klaar(waarde):
    if isinstance(waarde, (datetime, date)):
        return waarde.isoformat()
    return waarde


def maak_backup(con):
    """Leest alle tabellen uit en geeft een compleet, herstelbaar back-upbestand terug."""
    data, tellingen = {}, {}
    for tabel in TABELLEN:
        rijen = [{k: _json_klaar(v) for k, v in r.items()} for r in con.execute(f"SELECT * FROM {tabel}")]
        data[tabel] = rijen
        tellingen[tabel] = len(rijen)
    return {
        "versie": 1,
        "gemaakt_op": datetime.now().isoformat(timespec="seconds"),
        "tellingen": tellingen,
        "tabellen": data,
    }


def _huidige_sha(headers):
    """Git heeft de sha van de vorige versie nodig om een bestand bij te werken."""
    try:
        r = requests.get(f"https://api.github.com/repos/{BACKUP_REPO}/contents/{BACKUP_PAD}",
                         headers=headers, timeout=10)
        if r.ok:
            return r.json().get("sha")
    except Exception:
        pass
    return None


def push_naar_github(backup):
    """Schrijft de back-up naar de GitHub-repo. Gooit nooit een exception."""
    if not backup_actief():
        return {"verzonden": False, "reden": "geen GITHUB_TOKEN/BACKUP_REPO ingesteld",
                "tellingen": backup["tellingen"]}
    inhoud = json.dumps(backup, ensure_ascii=False, indent=1)
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    samenvatting = ", ".join(f"{t}: {n}" for t, n in backup["tellingen"].items() if n)
    body = {"message": f"Back-up {date.today().isoformat()} — {samenvatting}",
            "content": base64.b64encode(inhoud.encode()).decode()}
    sha = _huidige_sha(headers)
    if sha:
        body["sha"] = sha
    try:
        r = requests.put(f"https://api.github.com/repos/{BACKUP_REPO}/contents/{BACKUP_PAD}",
                         headers=headers, json=body, timeout=20)
        if r.ok:
            return {"verzonden": True, "repo": BACKUP_REPO, "bestand": BACKUP_PAD,
                    "bytes": len(inhoud), "tellingen": backup["tellingen"]}
        return {"verzonden": False, "reden": f"GitHub {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"verzonden": False, "reden": str(e)}
