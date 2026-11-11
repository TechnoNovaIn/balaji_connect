# Balaji Connect — Private Corporate Social Network & PWA

[![Django Tests](https://img.shields.io/badge/Django_Tests-76_Passed-success.svg)](#5-automated-testing)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![PWA Ready](https://img.shields.io/badge/PWA-Installable-blueviolet.svg)](#7-pwa--mobile-cellular-deployment)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#)

**Balaji Connect** is a secure, private enterprise social networking platform and Progressive Web App (PWA) built exclusively for the employees and leadership of **Balaji Transports**. It enables authorized personnel to share operational milestones, company photographs, vehicle fleet updates, and team memories, as well as engage in real-time direct messaging and birthday celebrations while strictly safeguarding internal communications behind corporate authentication.

---

## 1. System Architecture

```
                     ┌─────────────────────────────────────────────────────────┐
                     │          Employees on Mobile (Cellular Data) /          │
                     │          Desktop Browser / Progressive Web App          │
                     └────────────────────────────┬────────────────────────────┘
                                                  │ HTTPS / WSS
                                                  ▼
                     ┌─────────────────────────────────────────────────────────┐
                     │        Cloudflare Edge (Zero Trust Secure Tunnel)       │
                     │       - Free Automated SSL/TLS Certificates (HTTPS)     │
                     │       - DDoS Mitigation & WebSocket Full-Duplex Proxy   │
                     └────────────────────────────┬────────────────────────────┘
                                                  │ Outbound Encrypted Tunnel
                                                  ▼
                     ┌─────────────────────────────────────────────────────────┐
                     │          Local Company Server (cloudflared)             │
                     │     - Reverse proxy to Daphne ASGI (127.0.0.1:8000)     │
                     └────────────────────────────┬────────────────────────────┘
                                                  │
                                                  ▼
                     ┌─────────────────────────────────────────────────────────┐
                     │         Daphne ASGI + Django 5 Backend Core             │
                     │   - Session Auth + REST API Token Auth (DRF)            │
                     │   - Channels WebSockets (/ws/chat/<conv_id>/)           │
                     └─────────────┬───────────────────┬───────────────────────┘
                                   │                   │
         ┌─────────────────────────┴────────┐          └───────────────┐
         ▼                                  ▼                          ▼
┌──────────────────────────────┐ ┌──────────────────────┐ ┌──────────────────────────┐
│ PostgreSQL Database          │ │ Storage Driver       │ │ Channels Layer (Redis)   │
│ - Employees, Roles & Bios    │ │ - LocalStorageDriver │ ├──────────────────────────┤
│ - Posts, Reactions & Comments│ │ - GoogleDriveDriver  │ │ Service Worker (PWA Shell│
│ - 1-on-1 Chats & Messages    │ └──────────┬───────────┘ │  & Offline Fallback Cache│
│ - Birthday Notifications     │            ▼             └──────────────────────────┘
└──────────────────────────────┘ ┌──────────────────────┐
                                 │ Google Drive Vault   │
                                 │ (Personal 2TB OAuth) │
                                 └──────────────────────┘
```

---

## 2. Key Modules & Capabilities

### 🏢 Employee Authentication & Profiles
- **Company-Managed Access:** Self-registration is restricted. Accounts are provisioned and activated by administrators.
- **Dual Authentication:** Secure `HttpOnly` sessions for browser/PWA clients and encrypted tokens for native clients.
- **Modern Social Profiles:** 
  - Profile header features user avatar, name, and customizable **Bio**.
  - Quick-edit modal allows updating Display Name, Bio, Date of Birth, and Phone Number.
  - One-click **Direct Message** button on colleagues' profiles to launch instant conversations.

### 📱 Progressive Web App (PWA) & Offline Shell
- **Installable Native Feel:** Powered by [`manifest.json`](file:///e:/Balaji_Connect/frontend/static/manifest.json) (`display: standalone`) and high-resolution icons (192x192, 512x512, Apple touch icon).
- **Service Worker ([`sw.js`](file:///e:/Balaji_Connect/frontend/static/sw.js)):** Precaches application shell, stylesheets, scripts, and logos for lightning-fast loads on cellular data.
- **Branded Offline Fallback ([`offline.html`](file:///e:/Balaji_Connect/frontend/templates/offline.html)):** If the local server goes down or the employee loses signal, the app gracefully presents a branded offline card with an auto-reconnect polling mechanism every 15 seconds.

### 💬 Real-Time Direct Messaging (Chat)
- **Django Channels & WebSockets:** Full-duplex messaging over `/ws/chat/<conversation_id>/`.
- **1-on-1 Conversations:** Search colleagues, review chat history, send messages with Enter key, and track unread badge counters in the top navigation and sidebar.
- **Post Sharing to DM:** Share any company post directly into private chat with selected colleagues including custom notes.

### 🎂 Automated Birthday Celebrations (LinkedIn / Facebook Style)
- **Daily Birthday Dispatch:** Automatically evaluates employee birthdates (`date_of_birth`) on navigation or via automated cron/management command (`python manage.py send_birthday_notifications`).
- **Company-Wide Notification:** Dispatches celebration notices to colleagues (*"Today is [Name]'s birthday! Wish them a wonderful year ahead! 🎂"*).
- **Click-to-DM:** Tapping the notification or feed banner takes employees straight into a private chat with the celebrant to wish them happy birthday.
- **Feed Banner Auto-Dismissal:** Disappears from the feed once clicked, with a manual close button (`✕`) and daily session persistence.

### 📸 Secure Media Vault (Google Drive 2TB Integration)
- **Zero Public Exposure:** Google Drive files are never made public. Media streams are proxied through authenticated Django endpoints (`/api/v1/media/<id>/view/`) that verify employee permissions before streaming chunks.
- **Client-Side Instant Previews:** Immediate blob preview when choosing an image/video with upload status indicators.
- **Deduplication:** SHA-256 hash checks prevent duplicate files on network retries.

### 📰 Feed, Posts & Interactions
- **Chronological Feed:** Paginated feed with milestone badges and photo/video attachments.
- **Emoji & GIF Reactions:** Quick Like thumbs-up, full emoji palette, and animated reaction GIFs.
- **Post Options Modal (Instagram Style):** Delete own posts or share posts to colleagues.
- **Comment Threads:** Interactive comment reactions and author deletion controls.

---

## 3. Quick Start & Local Setup

### 3.1 Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- PostgreSQL (Active database: `balaji_connect`)
- Git

### 3.2 Installation

```bash
# Clone the repository
git clone <repo-url>
cd Balaji_Connect

# Create and activate virtual environment
python -m venv .venv

# Windows Powershell
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3.3 Database Migrations & Seeding

```bash
# Run migrations
python manage.py migrate

# (Optional) Seed initial departments, admin, staff, and posts
python manage.py seed_data
```

### 3.4 Running the Development Server

Balaji Connect uses **Daphne** as its ASGI server to support both HTTP and WebSockets simultaneously:

```bash
python manage.py runserver 127.0.0.1:8000


```
Open your browser and navigate to: `http://127.0.0.1:8000/`

---

## 4. Google Drive OAuth 2.0 Vault Configuration

Balaji Connect supports both local storage and Google Drive:

1. In the [Google Cloud Console](https://console.cloud.google.com/), enable the **Google Drive API**.
2. Create an **OAuth 2.0 Client ID** (Desktop Application).
3. Authorize with the `https://www.googleapis.com/auth/drive.file` scope using the helper script:
   ```bash
   python scripts/setup_gdrive_oauth.py
   ```
4. Set credentials in your `.env` file:
   ```env
   STORAGE_DRIVER=gdrive
   GOOGLE_DRIVE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret
   GOOGLE_DRIVE_REFRESH_TOKEN=your-refresh-token
   GOOGLE_DRIVE_FOLDER_ID=your-folder-id
   ```

---

## 5. Automated Testing

Run the comprehensive test suite (**76 automated tests** covering authentication, permissions, media vault streaming, posts, reactions, comments, direct messaging, birthday dispatch, content moderation, and PWA endpoints):

```bash
python manage.py test --noinput
```

---

## 6. Birthday Engine Management Command

To trigger daily birthday checks manually or via scheduled cron/Task Scheduler:

```bash
python manage.py send_birthday_notifications
```

---

## 7. PWA & Mobile Cellular Deployment

To deploy on your company's on-premise local server and make it accessible worldwide to employees over mobile cellular data:

### 1. Cloudflare Tunnel (`cloudflared`)
- Sign up for a free Cloudflare account and add your domain (e.g., `yourcompany.com`).
- Enable **WebSockets** in Cloudflare Dashboard ➔ **Network**.
- Install `cloudflared` on the company server and create a tunnel routed to `localhost:8000`.
- In `config/settings.py`, configure:
  ```python
  ALLOWED_HOSTS = ['connect.yourcompany.com', '127.0.0.1', 'localhost']
  CSRF_TRUSTED_ORIGINS = ['https://connect.yourcompany.com']
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  ```

### 2. Installing the PWA on Mobile
- **Android (Chrome):** Open `https://connect.yourcompany.com`. Tap **"Install App"** from the banner or dropdown menu.
- **iPhone / iPad (Safari):** Open the site, tap the **Share** button ➔ select **"Add to Home Screen"**.
- The app installs as a standalone native-like icon on the phone home screen with full offline resilience.

### 3. Server Resilience & 24/7 Autostart
- **BIOS Auto-Power On:** In PC BIOS, set `AC Power Recovery` to `Power On` so the server restarts automatically when power returns after an outage.
- **Windows Service (NSSM):** Register Daphne and Cloudflare Tunnel as Windows services to run automatically in the background on boot without requiring user desktop login.
- **Database Safety:** PostgreSQL transaction write-ahead logging (WAL) guarantees all committed data remains completely intact during unexpected power loss.


-**Admin_Username:** BT-0001 -**Password:**DemoPass123!
-**Employee:** BT-1001  -**Password:**DemoPass123!