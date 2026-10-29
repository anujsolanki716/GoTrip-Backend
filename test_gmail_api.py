
import base64
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    token_path = Path("token.json")

    if not token_path.exists():
        raise FileNotFoundError("token.json backend folder mein nahi mili.")

    creds = Credentials.from_authorized_user_file(
        str(token_path), SCOPES
    )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(
                creds.to_json(), encoding="utf-8"
            )
        else:
            raise RuntimeError(
                "Gmail authorization invalid hai. "
                "authorize_gmail.py dobara run karo."
            )

    # Pehle apne hi Gmail par test karo.
    to_email = input("Test email address enter karo: ").strip()

    if not to_email or "@" not in to_email:
        raise ValueError("Valid email address enter karo.")

    message = EmailMessage()
    message["To"] = to_email
    message["From"] = "me"
    message["Subject"] = "GoTrip Gmail API Test"
    message.set_content(
        "Hello! GoTrip backend se Gmail API test email successful hai."
    )

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    service = build(
        "gmail", "v1",
        credentials=creds,
        cache_discovery=False,
    )

    result = service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()

    print("Email accepted by Gmail API.")
    print("Message ID:", result.get("id"))
    print("Check your inbox and spam folder.")


if __name__ == "__main__":
    main()
