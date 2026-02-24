import os
import smtplib
from email.message import EmailMessage


def send_email(to_email: str, subject: str, body: str) -> bool:
    host = os.getenv("COEVO_SMTP_HOST", "").strip()
    port = int(os.getenv("COEVO_SMTP_PORT", "587"))
    user = os.getenv("COEVO_SMTP_USER", "").strip()
    password = os.getenv("COEVO_SMTP_PASSWORD", "").strip()
    from_email = os.getenv("COEVO_SMTP_FROM", user or "no-reply@coevo.local")

    if not host or not to_email:
        return False

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
    return True
