"""E-mailverzending via Resend.

Zonder RESEND_API_KEY wordt er niets verstuurd maar geeft stuur_mail de
opgebouwde mail terug — zo blijft de app (en de demo-omgeving) overal werken
en is de inhoud lokaal te controleren.
"""
import os

import requests

RESEND_KEY = os.environ.get("RESEND_API_KEY")
MAIL_FROM = os.environ.get("MAIL_FROM", "Leadgenerator Felison <onboarding@resend.dev>")
APP_URL = os.environ.get("APP_URL", "https://afm-leadgenerator.vercel.app")


def mail_actief():
    return bool(RESEND_KEY)


def _template(titel, regels, knop_tekst="Open de leadgenerator"):
    """Eenvoudige HTML-mail in Felison-stijl. `regels` is een lijst HTML-strings."""
    inhoud = "".join(f'<p style="margin:0 0 10px;font-size:14px;line-height:1.6;color:#1D2433">{r}</p>' for r in regels)
    return f"""
<div style="background:#EFF1F4;padding:28px 12px;font-family:-apple-system,'Segoe UI',Arial,sans-serif">
  <div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #EAECF0;border-radius:14px;padding:28px">
    <div style="font-size:22px;font-weight:800;color:#0A0AA0;letter-spacing:-1px;margin-bottom:2px">felison</div>
    <div style="font-size:10px;letter-spacing:.16em;color:#98A2B3;font-weight:700;margin-bottom:18px">LEADGENERATOR</div>
    <h2 style="margin:0 0 14px;font-size:17px;color:#1D2433">{titel}</h2>
    {inhoud}
    <a href="{APP_URL}" style="display:inline-block;margin-top:16px;background:#2E90FA;color:#fff;text-decoration:none;
       font-size:14px;font-weight:600;padding:10px 18px;border-radius:10px">{knop_tekst}</a>
    <p style="margin:18px 0 0;font-size:11.5px;color:#98A2B3">Automatisch bericht van de Leadgenerator Felison.</p>
  </div>
</div>"""


def stuur_mail(naar, onderwerp, titel, regels, knop_tekst="Open de leadgenerator"):
    """Verstuurt een mail; geeft dict met resultaat terug. Gooit nooit een exception."""
    html = _template(titel, regels, knop_tekst)
    if not naar:
        return {"verzonden": False, "reden": "geen ontvanger ingesteld", "onderwerp": onderwerp}
    if not RESEND_KEY:
        return {"verzonden": False, "reden": "geen RESEND_API_KEY", "naar": naar,
                "onderwerp": onderwerp, "voorbeeld": regels}
    try:
        r = requests.post("https://api.resend.com/emails",
                          headers={"Authorization": f"Bearer {RESEND_KEY}",
                                   "Content-Type": "application/json"},
                          json={"from": MAIL_FROM, "to": [naar], "subject": onderwerp, "html": html},
                          timeout=10)
        if r.ok:
            return {"verzonden": True, "naar": naar, "onderwerp": onderwerp}
        return {"verzonden": False, "reden": f"Resend {r.status_code}: {r.text[:200]}", "naar": naar}
    except Exception as e:
        return {"verzonden": False, "reden": str(e), "naar": naar}
