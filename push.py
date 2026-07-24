"""Web Push (VAPID) — echte notificaties op iPhone/Android.

Let op (Apple/WebKit): iOS levert push alleen aan een webapp die via
"Zet op beginscherm" is geïnstalleerd. Een gewoon Safari-tabblad krijgt niets.

Sleutels komen uit omgevingsvariabelen: ze moeten stabiel blijven (bij wijziging
vervallen alle abonnementen) en mogen nooit in de back-up naar GitHub belanden.
"""
import json
import os

VAPID_PUBLIC = os.environ.get("VAPID_PUBLIC")
VAPID_PRIVATE = os.environ.get("VAPID_PRIVATE")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:p.doets@felison.nl")


def push_actief():
    return bool(VAPID_PUBLIC and VAPID_PRIVATE)


def stuur_push(con, identiteit, titel, tekst, url="/", tag="leadgenerator"):
    """Stuurt naar alle apparaten van één identiteit. Gooit nooit een exception.

    Verlopen abonnementen (404/410 = app verwijderd of opnieuw geïnstalleerd)
    worden meteen opgeruimd, anders blijft de lijst vollopen met dode apparaten.
    """
    if not push_actief():
        return {"verzonden": 0, "reden": "geen VAPID-sleutels ingesteld"}
    abonnementen = list(con.execute(
        "SELECT * FROM push_abonnementen WHERE identiteit=?", (identiteit,)))
    if not abonnementen:
        return {"verzonden": 0, "reden": f"geen apparaten aangemeld voor '{identiteit}'"}

    from pywebpush import webpush, WebPushException
    lading = json.dumps({"titel": titel, "tekst": tekst, "url": url, "tag": tag})
    gelukt, opgeruimd, fouten = 0, 0, []
    for ab in abonnementen:
        try:
            webpush(
                subscription_info={"endpoint": ab["endpoint"],
                                   "keys": {"p256dh": ab["p256dh"], "auth": ab["auth"]}},
                data=lading,
                vapid_private_key=VAPID_PRIVATE,
                vapid_claims={"sub": VAPID_SUBJECT},
                timeout=10,
            )
            gelukt += 1
        except WebPushException as e:
            code = getattr(e.response, "status_code", None)
            if code in (404, 410):
                con.execute("DELETE FROM push_abonnementen WHERE endpoint=?", (ab["endpoint"],))
                opgeruimd += 1
            else:
                fouten.append(f"{code}: {str(e)[:120]}")
        except Exception as e:
            fouten.append(str(e)[:120])
    if opgeruimd:
        con.commit()
    uit = {"verzonden": gelukt, "identiteit": identiteit}
    if opgeruimd:
        uit["opgeruimde_apparaten"] = opgeruimd
    if fouten:
        uit["fouten"] = fouten
    return uit
