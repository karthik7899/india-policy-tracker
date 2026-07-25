"""Failure alerting for the scheduled briefing.

Until now a broken run was invisible. A crash failed the workflow silently, and
a *degraded* run — Yahoo returning nothing, Screener rate-limiting the whole
fetch — did not even do that: the briefing rendered from whatever survived, the
email went out, the job reported success. health.py now fails the job on
degradation; this delivers the news.

Deliberately standard library only, and deliberately not importing anything
else from this repo. The failure being reported might be the dependency
install itself, in which case a module that needs `requests` or the project's
logger could not run to tell you about it.
"""

import os
import smtplib
import sys
from email.mime.text import MIMEText

_SUBJECT = "🚨 India Policy Briefing: run FAILED"


def _body(run_url: str, run_number: str, sha: str) -> str:
    return f"""<html><body style="font-family: system-ui, sans-serif;">
<h2 style="color:#b91c1c; margin-bottom:4px;">Daily briefing run failed</h2>
<p style="color:#475569; margin-top:0;">
  The scheduled pipeline did not complete cleanly, so today's dashboard and
  watchlist were <strong>not</strong> committed — yesterday's data is still in
  place.
</p>
<p><strong>Run:</strong> #{run_number or "?"}<br>
   <strong>Commit:</strong> {sha[:7] if sha else "unknown"}</p>
<p><a href="{run_url}" style="color:#2563eb;">Open the run log</a></p>
<p style="color:#64748b; font-size:13px;">
  Either a step raised, or the run finished with degraded coverage — too few
  holdings priced, no Screener fundamentals, or empty analysis output. The log
  lines beginning "Run health:" say which.
</p>
</body></html>"""


def send_failure_alert() -> bool:
    """Email the owner that the run failed. Returns True when sent."""
    raw = os.environ.get("RECEIVER_EMAIL", "")
    receivers = [e.strip() for e in raw.split(",") if e.strip()]
    server = os.environ.get("SMTP_SERVER")
    port = os.environ.get("SMTP_PORT")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")

    if not all([receivers, server, port, username, password]):
        print("Failure alert skipped: SMTP settings are not fully configured.")
        return False

    msg = MIMEText(
        _body(
            os.environ.get("RUN_URL", ""),
            os.environ.get("RUN_NUMBER", ""),
            os.environ.get("RUN_SHA", ""),
        ),
        "html",
    )
    msg["Subject"] = _SUBJECT
    msg["From"] = username
    msg["To"] = ", ".join(receivers)

    try:
        port_num = int(port)
        if port_num == 465:
            smtp = smtplib.SMTP_SSL(server, port_num, timeout=30)
        else:
            smtp = smtplib.SMTP(server, port_num, timeout=30)
            smtp.starttls()
        with smtp:
            smtp.login(username, password)
            smtp.sendmail(username, receivers, msg.as_string())
        print("Failure alert sent.")
        return True
    except Exception as e:  # noqa: BLE001 - the alert must never mask the failure
        print(f"Failure alert could not be sent: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    # Always exit 0: this runs *because* the job already failed, and an alert
    # that cannot send must not overwrite that failure with its own.
    send_failure_alert()
    sys.exit(0)
