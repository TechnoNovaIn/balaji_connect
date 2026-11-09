"""
Balaji Connect - Google Drive OAuth Setup Helper
------------------------------------------------
This script automates generating the GOOGLE_DRIVE_REFRESH_TOKEN and
saving it directly into your .env file.
"""

import os
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Error: google-auth-oauthlib is required. Run: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/drive.file']
ENV_FILE = Path(__file__).resolve().parent.parent / '.env'

def read_env_var(key):
    if not ENV_FILE.exists():
        return ''
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split('=', 1)[1].strip()
    return ''

def update_env_file(updates: dict):
    lines = []
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    keys_to_update = set(updates.keys())
    new_lines = []
    for line in lines:
        stripped = line.strip()
        matched_key = None
        for k in keys_to_update:
            if stripped.startswith(f"{k}="):
                matched_key = k
                break
        if matched_key:
            new_lines.append(f"{matched_key}={updates[matched_key]}\n")
            keys_to_update.remove(matched_key)
        else:
            new_lines.append(line)

    for k in keys_to_update:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n')
        new_lines.append(f"{k}={updates[k]}\n")

    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def main():
    print("=" * 65)
    print("      Balaji Connect - Google Drive Authorization Setup")
    print("=" * 65)
    print()

    client_id = read_env_var('GOOGLE_DRIVE_CLIENT_ID') or os.getenv('GOOGLE_DRIVE_CLIENT_ID', '').strip()
    client_secret = read_env_var('GOOGLE_DRIVE_CLIENT_SECRET') or os.getenv('GOOGLE_DRIVE_CLIENT_SECRET', '').strip()

    if not client_id:
        client_id = input("Enter your Google OAuth Client ID: ").strip()
    else:
        print(f"Using Client ID: {client_id[:20]}...")

    if not client_secret:
        client_secret = input("Enter your Google OAuth Client Secret: ").strip()
    else:
        print("Using Client Secret from .env")

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost", "http://127.0.0.1"]
        }
    }

    print()
    print("Opening your browser to authorize Balaji Connect with Google Drive...")
    print("1. Select your Google account.")
    print("2. If you see 'Google hasn't verified this app', click 'Advanced' -> 'Go to Balaji Connect (unsafe)'.")
    print("3. Click 'Continue' / 'Allow' to authorize.")
    print()

    try:
        flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
        prompt_msg = (
            "\n" + "=" * 65 + "\n"
            "CLICK THIS EXACT LINK TO AUTHORIZE DARSHANBT10@GMAIL.COM:\n"
            "{url}\n"
            + "=" * 65 + "\n"
        )
        creds = flow.run_local_server(
            port=8090,
            prompt='consent',
            access_type='offline',
            open_browser=True,
            authorization_prompt_message=prompt_msg
        )
    except Exception as e:
        print(f"Authorization failed: {e}")
        return

    refresh_token = creds.refresh_token
    if not refresh_token:
        print("Warning: Google did not return a refresh token. Try revoking app access at https://myaccount.google.com/permissions and run again.")
        return

    # Automatically create the Balaji_Connect_Vault folder in the authenticated account's Drive
    folder_id = ''
    try:
        from googleapiclient.discovery import build
        drive_service = build('drive', 'v3', credentials=creds)
        about = drive_service.about().get(fields='user').execute()
        user_email = about.get('user', {}).get('emailAddress', 'Unknown User')
        print(f"\nSuccessfully authenticated as: {user_email}")

        folder_meta = {
            'name': 'Balaji_Connect_Vault',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=folder_meta, fields='id, name, webViewLink').execute()
        folder_id = folder.get('id')
        print(f"Created dedicated vault folder: {folder.get('name')} (ID: {folder_id})")
        print(f"Google Drive Link: {folder.get('webViewLink')}")
    except Exception as e:
        print(f"Notice: Could not automatically create folder ({e}). Using existing folder ID if present.")
        folder_id = read_env_var('GOOGLE_DRIVE_FOLDER_ID')

    # Update .env automatically
    env_updates = {
        'STORAGE_DRIVER': 'gdrive',
        'GOOGLE_DRIVE_CLIENT_ID': client_id,
        'GOOGLE_DRIVE_CLIENT_SECRET': client_secret,
        'GOOGLE_DRIVE_REFRESH_TOKEN': refresh_token,
    }
    if folder_id:
        env_updates['GOOGLE_DRIVE_FOLDER_ID'] = folder_id

    update_env_file(env_updates)

    print()
    print("=" * 65)
    print("SUCCESS! Google Drive is now configured for Balaji Connect!")
    print(f"Refresh Token: {refresh_token[:15]}... (saved to .env)")
    if folder_id:
        print(f"Vault Folder ID: {folder_id} (saved to .env)")
    print("STORAGE_DRIVER has been set to 'gdrive' in your .env file.")
    print("=" * 65)
    print()
    print("You can now start your server:")
    print("  python manage.py runserver 127.0.0.1:8000")
    print()

if __name__ == '__main__':
    main()


