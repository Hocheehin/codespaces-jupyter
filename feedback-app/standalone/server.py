"""Standalone server for the QR Code Feedback & FacilityBot app (OPS_SOP_3.4_06).

Public (no login):  the QR page - pick a site, then Feedback or Service request, then submit.
Staff (password):   Operations, Department, Dashboard and Monthly report.

Run:  STAFF_PASSWORD=choose-one python server.py      (then open http://localhost:8000)
"""
import hmac
import json
import os
import secrets
import sqlite3
import string
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, abort, jsonify, request, session

BASE = os.path.dirname(os.path.abspath(__file__))
APP_HTML = os.path.join(BASE, "..", "app.html")
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE, "cases.db"))

# Keep these in step with SITES / CATS / DEPTS in app.html.
SITES = ["Site 1", "Site 2", "Site 3"]
CATS = {"feedback": ["Compliment", "Suggestion", "Complaint"], "facility": ["Fault", "Repair"]}
ROLES = ["Resident", "Family member", "Visitor"]

STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD")
if not STAFF_PASSWORD:
    STAFF_PASSWORD = secrets.token_urlsafe(9)
    print(f"\n  No STAFF_PASSWORD set. Staff password for this run: {STAFF_PASSWORD}\n", flush=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=200 * 1024,
)


# ---------- storage ----------
def db():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)"
    )
    return con


def iso_now():
    d = datetime.now(timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def new_id(tab, con):
    ym = datetime.now(timezone.utc).strftime("%y%m")
    prefix = "FB-" if tab == "feedback" else "FR-"
    alphabet = string.ascii_uppercase + string.digits
    while True:
        cid = f"{prefix}{ym}-{''.join(secrets.choice(alphabet) for _ in range(4))}"
        if not con.execute("SELECT 1 FROM cases WHERE id=?", (cid,)).fetchone():
            return cid


# ---------- simple rate limiting (per IP, in memory) ----------
_hits = defaultdict(deque)


def limited(key, limit, window_s):
    now = time.time()
    q = _hits[key]
    while q and q[0] < now - window_s:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() or request.remote_addr or "?"


def require_staff():
    if not session.get("staff"):
        abort(401)


@app.errorhandler(401)
def _401(_):
    return jsonify(error="Sign in required"), 401


def text(body, key, maxlen):
    v = body.get(key, "")
    return v.strip()[:maxlen] if isinstance(v, str) else ""


# ---------- pages ----------
@app.get("/")
def index():
    with open(APP_HTML, encoding="utf-8") as f:
        page = f.read()
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0}img{max-width:100%}</style></head><body>" + page + "</body></html>"
    )
    return Response(html, mimetype="text/html", headers={"Cache-Control": "no-store"})


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; "
        "frame-ancestors 'none'"
    )
    return resp


# ---------- API ----------
@app.get("/api/me")
def me():
    return jsonify(staff=bool(session.get("staff")))


@app.post("/api/login")
def login():
    if limited(("login", client_ip()), 10, 600):
        return jsonify(error="Too many attempts"), 429
    body = request.get_json(silent=True) or {}
    pw = body.get("password", "")
    if isinstance(pw, str) and hmac.compare_digest(pw.encode(), STAFF_PASSWORD.encode()):
        session.clear()
        session.permanent = True
        session["staff"] = True
        return jsonify(staff=True)
    return jsonify(error="Wrong password"), 401


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(staff=False)


@app.post("/api/cases")
def create_case():
    """Public: anyone who scans the QR code. Only the fields a resident fills in are accepted."""
    if limited(("submit", client_ip()), 20, 600):
        return jsonify(error="Too many submissions"), 429
    b = request.get_json(silent=True) or {}
    tab = b.get("tab")
    if tab not in CATS:
        return jsonify(error="Choose Feedback or Service request."), 400
    if b.get("category") not in CATS[tab]:
        return jsonify(error="Choose a type."), 400
    if b.get("site") not in SITES:
        return jsonify(error="Choose your site."), 400
    desc = text(b, "description", 2000)
    if len(desc) < 5:
        return jsonify(error="Please describe it in a few words."), 400
    role = b.get("role") if b.get("role") in ROLES else "Visitor"
    now = iso_now()
    with db() as con:
        case = {
            "id": new_id(tab, con), "tab": tab, "category": b["category"], "site": b["site"],
            "location": text(b, "location", 200), "description": desc,
            "name": text(b, "name", 100), "contact": text(b, "contact", 150), "role": role,
            "createdAt": now, "updatedAt": now, "ackAt": None, "dept": None, "assignedAt": None,
            "info": "", "closedAt": None, "closeNote": "",
            "updates": [{"at": now, "kind": "system", "who": "System",
                         "text": "Feedback submitted through QR code" if tab == "feedback"
                         else "Service request submitted through QR code (FacilityBot)"}],
        }
        con.execute("INSERT INTO cases VALUES (?,?,?)", (case["id"], now, json.dumps(case)))
    # The sender only gets their reference number back, never other cases.
    return jsonify(id=case["id"], tab=tab), 201


@app.get("/api/cases")
def list_cases():
    require_staff()
    with db() as con:
        rows = con.execute("SELECT data FROM cases ORDER BY created_at DESC").fetchall()
    return jsonify(cases=[json.loads(r[0]) for r in rows])


@app.put("/api/cases/<cid>")
def update_case(cid):
    require_staff()
    b = request.get_json(silent=True)
    if not isinstance(b, dict):
        return jsonify(error="Bad request"), 400
    with db() as con:
        row = con.execute("SELECT data FROM cases WHERE id=?", (cid,)).fetchone()
        if not row:
            return jsonify(error="Case not found"), 404
        old = json.loads(row[0])
        new = {**old, **b}
        for fixed in ("id", "tab", "createdAt", "name", "contact", "description", "site"):
            new[fixed] = old.get(fixed)  # what the sender submitted can't be rewritten
        new["updatedAt"] = iso_now()
        con.execute("UPDATE cases SET data=? WHERE id=?", (json.dumps(new), cid))
    return jsonify(new)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"  Open http://localhost:{port}  (QR page)   ·   http://localhost:{port}/#ops  (staff)", flush=True)
    app.run(host="0.0.0.0", port=port)
