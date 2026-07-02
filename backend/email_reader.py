import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
from typing import Optional

_EMAIL_CONFIG = None

def _get_email_config():
    global _EMAIL_CONFIG
    if _EMAIL_CONFIG:
        return _EMAIL_CONFIG
    address = os.getenv("GMAIL_ADDRESS", "") or os.getenv("EMAIL_ADDRESS", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "") or os.getenv("EMAIL_APP_PASSWORD", "")
    if address and password:
        _EMAIL_CONFIG = {"address": address, "password": password}
    return _EMAIL_CONFIG

def set_email_config(address: str, password: str):
    global _EMAIL_CONFIG
    _EMAIL_CONFIG = {"address": address, "password": password}

def email_configured() -> bool:
    return _get_email_config() is not None

def get_setup_instructions() -> str:
    return (
        "To let me read your Gmail, I need an App Password:\n"
        "1. Go to https://myaccount.google.com/apppasswords\n"
        "   (You may need to enable 2-Step Verification first)\n"
        "2. Under 'Select app', choose 'Mail'\n"
        "3. Under 'Select device', choose 'Other'\n"
        "4. Type 'SODA' and click GENERATE\n"
        "5. Copy the 16-character password (it looks like 'xxxx xxxx xxxx xxxx')\n"
        "6. Tell me your Gmail address and the app password\n\n"
        "Example: 'myemail@gmail.com' and 'abcd efgh ijkl mnop'"
    )

def decode_mime_header(header_value: str) -> str:
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                parts.append(part.decode("utf-8", errors="replace"))
        else:
            parts.append(str(part))
    return " ".join(parts)

def _get_email_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body += payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        body += payload.decode("utf-8", errors="replace")
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        text = payload.decode(charset, errors="replace")
                        text = re.sub(r'<[^>]+>', ' ', text)
                        text = re.sub(r'\s+', ' ', text).strip()
                        body += text[:2000]
                    except (LookupError, UnicodeDecodeError):
                        pass
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body = payload.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                body = payload.decode("utf-8", errors="replace")
    return body.strip()[:5000]

async def read_emails(query: str = "", max_results: int = 10) -> dict:
    config = _get_email_config()
    if not config:
        return {"success": False, "error": "Email not configured", "setup_instructions": get_setup_instructions()}

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(config["address"], config["password"])
        mail.select("INBOX")

        search_criteria = query.strip() if query else "UNSEEN"
        if search_criteria.upper() == "ALL":
            search_criteria = "ALL"
        elif search_criteria.upper() == "UNSEEN":
            pass
        elif search_criteria.upper() == "UNREAD":
            search_criteria = "UNSEEN"

        status, message_ids = mail.search(None, search_criteria)
        if status != "OK":
            mail.logout()
            return {"success": False, "error": f"IMAP search failed: {status}"}

        ids = message_ids[0].split() if message_ids[0] else []
        if not ids:
            mail.logout()
            return {"success": True, "emails": [], "total": 0, "message": "No emails found"}

        ids = ids[-max_results:]
        emails = []

        for msg_id in reversed(ids):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_mime_header(msg.get("Subject", ""))
            sender = decode_mime_header(msg.get("From", ""))
            date = msg.get("Date", "")
            message_id = msg.get("Message-ID", "")
            body = _get_email_body(msg)

            emails.append({
                "id": message_id or str(msg_id, "utf-8"),
                "subject": subject or "(no subject)",
                "from": sender,
                "date": date,
                "body": body[:2000],
                "preview": body[:150].replace("\n", " "),
            })

        mail.logout()
        return {"success": True, "emails": emails, "total": len(emails)}

    except imaplib.IMAP4.error as e:
        error_str = str(e)
        if "LOGIN" in error_str.upper() or "AUTHENTICATION" in error_str.upper():
            return {
                "success": False, "error": "Login failed. Use an App Password, not your regular password.",
                "setup_instructions": get_setup_instructions(),
            }
        return {"success": False, "error": f"IMAP error: {error_str}"}
    except Exception as e:
        return {"success": False, "error": f"Email read failed: {str(e)}"}


async def send_email(to: str, subject: str, body: str) -> dict:
    config = _get_email_config()
    if not config:
        return {"success": False, "error": "Email not configured", "setup_instructions": get_setup_instructions()}

    try:
        msg = MIMEMultipart()
        msg["From"] = config["address"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(config["address"], config["password"])
        server.sendmail(config["address"], to, msg.as_string())
        server.quit()

        return {"success": True, "message": f"Email sent to {to}"}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False, "error": "SMTP login failed. Use an App Password.",
            "setup_instructions": get_setup_instructions(),
        }
    except Exception as e:
        return {"success": False, "error": f"Email send failed: {str(e)}"}
