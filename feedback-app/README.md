# QR Code Feedback & FacilityBot prototype (OPS_SOP_3.4_06)

A single-page prototype for testing whether the SOP process flow works in practice.

| View | SOP step |
|---|---|
| `#scan` – QR page | Resident, family or visitor scans the QR code, picks their site (Site 1, 2 or 3), then sees two buttons only: **Feedback** (compliment / suggestion / complaint) or **Service request** (FacilityBot: fault / repair). Tapping one opens its form |
| `#ops` – Operations | Log and acknowledge (feedback must be acknowledged within 1 working day, so late cases are flagged) or receive the fault report, then assign to a department with information. Then either "Not resolved: ask the department for status" or "Resolved: close the case and inform the sender" |
| `#dept` – Department | The department acts and updates Operations |
| `#report` – Monthly report | Monthly report to the HONH: counts by type and department, acknowledgement rate, average time to close, open cases. You can copy it as text |

## Run it
Open `index.html` in a browser. Cases are saved in that browser's localStorage, and "Load example cases" fills in sample data.
`app.html` is the same page without the document wrapper. It is used for the hosted version, which shares cases across devices.

A real QR code would encode the page URL with `#scan` on the end.

## Standalone app (no Claude account needed)

`standalone/server.py` runs the same screens as a normal website with its own database:

- **Residents, families, visitors:** open the QR link, pick a site, then Feedback or Service request, and submit. No login. They only get their reference number back and can never see other cases.
- **Staff:** Operations, Department, Dashboard and Monthly report ask for the staff password. Staff stay signed in for 12 hours, and the case list refreshes every 8 seconds.
- **Data:** cases are kept in a SQLite file (`cases.db`).

### Try it in a GitHub Codespace (quickest way to test with real phones)
1. On GitHub, open this repo on branch `ccr-68e33433-5cgakz`, then **Code → Codespaces → Create codespace**.
2. In the Codespace terminal:
   ```bash
   pip install -r feedback-app/standalone/requirements.txt
   STAFF_PASSWORD=choose-a-password python feedback-app/standalone/server.py
   ```
3. Open the **Ports** tab. Right-click port **8000**, choose **Port Visibility → Public**, then copy the forwarded address (it looks like `https://<name>-8000.app.github.dev`).
4. Make the QR poster for that address:
   ```bash
   python feedback-app/standalone/make_qr.py https://<name>-8000.app.github.dev feedback-app/qr-poster.png
   ```
5. Residents scan the poster. Staff open the same address with `#ops` on the end and sign in.

A Codespace stops after about 30 minutes without use, and the address changes if you make a new one. That's fine for a pilot but not for permanent use.

### Run it permanently
Use the `Dockerfile` on any host that runs containers (your IT team's server, Azure App Service, Render, Railway and similar):
```bash
docker build -t feedback-app feedback-app
docker run -p 8000:8000 -v feedback-data:/data \
  -e STAFF_PASSWORD=... -e SECRET_KEY=$(openssl rand -hex 32) -e COOKIE_SECURE=1 feedback-app
```
- Keep `/data` on persistent storage, because it holds the database.
- Serve it over HTTPS.
- Back up `cases.db`.
- Sites and departments are listed in both `app.html` and `standalone/server.py`. Change them in both places.

Before using it with real residents' details, check it with your IT and data-protection team (PDPA). This pilot uses one shared staff password and doesn't have per-person staff accounts.
