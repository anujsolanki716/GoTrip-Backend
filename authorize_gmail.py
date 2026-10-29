
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    credentials_file = Path("credentials.json")
    token_file = Path("token.json")

    if not credentials_file.exists():
        raise FileNotFoundError(
            "credentials.json backend folder mein nahi mili."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_file),
        SCOPES,
    )

    # Browser khulega; usmein GoTrip sender Gmail se sign in karo.
    creds = flow.run_local_server(
        host="localhost",
        port=0,
        open_browser=True,
    )

    token_file.write_text(creds.to_json(), encoding="utf-8")

    token_data = json.loads(creds.to_json())

    print("\nAuthorization successful.")
    print("Token saved to token.json")
    print("Client ID:", token_data.get("client_id"))
    print("Refresh token received:", bool(token_data.get("refresh_token")))

    if not token_data.get("refresh_token"):
        print(
            "WARNING: Refresh token nahi mila. "
            "Dobara authorization karni pad sakti hai."
        )


if __name__ == "__main__":
    main()
