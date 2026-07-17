"""Volledige back-up van alle tabellen, en het wegschrijven ervan naar GitHub.

Waarom één rollend bestand in plaats van één bestand per dag: Git bewaart zelf
elke versie (en slaat alleen de verschillen op). Eén bestand per dag zou elke
dag een volledige kopie zijn — bij duizenden leads loopt dat in de gigabytes.
Nu blijft de repo klein en is elke dag terug te halen via de bestandshistorie.

Token en repo komen uit de instellingen in de app (zodat niemand het
Vercel-dashboard in hoeft); een omgevingsvariabele blijft werken als fallback.
"""
import base64
import json
import os
from datetime import date, datetime

import requests

BACKUP_PAD = os.environ.get("BACKUP_PAD", "backup/leadgenerator-backup.json")

# Instellingen die nooit in de back-up mogen belanden: de back-up gaat naar
# GitHub, en een token in een repo wordt (terecht) direct ingetrokken.
GEHEIME_INSTELLINGEN = {"github_token"}

# Alle tabellen die samen de volledige staat van de app vormen.
TABELLEN = ["leads", "status_log", "contactmomenten", "lead_historie", "ams",
            "relaties", "instellingen", "presentje_types", "imports", "feedback"]


def _json_klaar(waarde):
    if isinstance(waarde, (datetime, date)):
        return waarde.isoformat()
    return waarde


def maak_backup(con):
    """Leest alle tabellen uit en geeft een compleet, herstelbaar back-upbestand terug."""
    data, tellingen = {}, {}
    for tabel in TABELLEN:
        rijen = [{k: _json_klaar(v) for k, v in r.items()} for r in con.execute(f"SELECT * FROM {tabel}")]
        if tabel == "instellingen":
            rijen = [r for r in rijen if r.get("sleutel") not in GEHEIME_INSTELLINGEN]
        data[tabel] = rijen
        tellingen[tabel] = len(rijen)
    return {
        "versie": 1,
        "gemaakt_op": datetime.now().isoformat(timespec="seconds"),
        "tellingen": tellingen,
        "tabellen": data,
    }


def _huidige_sha(headers, repo):
    """Git heeft de sha van de vorige versie nodig om een bestand bij te werken."""
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/contents/{BACKUP_PAD}",
                         headers=headers, timeout=10)
        if r.ok:
            return r.json().get("sha")
    except Exception:
        pass
    return None


def push_naar_github(backup, token, repo):
    """Schrijft de back-up naar de GitHub-repo. Gooit nooit een exception."""
    if not (token and repo):
        return {"verzonden": False, "reden": "geen GitHub-token/repo ingesteld",
                "tellingen": backup["tellingen"]}
    inhoud = json.dumps(backup, ensure_ascii=False, indent=1)
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    samenvatting = ", ".join(f"{t}: {n}" for t, n in backup["tellingen"].items() if n)
    body = {"message": f"Back-up {date.today().isoformat()} — {samenvatting}",
            "content": base64.b64encode(inhoud.encode()).decode()}
    sha = _huidige_sha(headers, repo)
    if sha:
        body["sha"] = sha
    try:
        r = requests.put(f"https://api.github.com/repos/{repo}/contents/{BACKUP_PAD}",
                         headers=headers, json=body, timeout=20)
        if r.ok:
            return {"verzonden": True, "repo": repo, "bestand": BACKUP_PAD,
                    "bytes": len(inhoud), "tellingen": backup["tellingen"]}
        # GitHub's foutmelding bevat het token niet, maar wel de repo-naam — prima
        # om terug te geven, het helpt bij typefouten in de repo-naam.
        return {"verzonden": False, "reden": f"GitHub {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"verzonden": False, "reden": str(e)}
