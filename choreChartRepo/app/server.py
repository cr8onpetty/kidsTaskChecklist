#!/usr/bin/env python3
"""Chore Chart server for Raspberry Pi.

Serves a touch-friendly chore checklist at http://localhost:8080 and records
which chores each kid finished each day in data/history.json.
Uses only the Python standard library - nothing to pip install.
"""
import json
import os
import re
import threading
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "chores.json")
DATA_DIR = os.path.join(BASE, "data")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")
STATIC_DIR = os.path.join(BASE, "static")
PORT = int(os.environ.get("CHORE_PORT", "8080"))
HOST = os.environ.get("CHORE_HOST", "0.0.0.0")  # 0.0.0.0 = also reachable from phones on your Wi-Fi

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # Python weekday() order
lock = threading.Lock()


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_config():
    # Re-read on every request so edits to chores.json show up after a page refresh.
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {}
    with open(HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_history(hist):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = HISTORY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=1, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, HISTORY_PATH)  # atomic, so a power cut can't corrupt the file


def chores_for(cfg, kid, day):
    """Return {section_id: [chore dicts]} for one kid on one date."""
    wd = DAYS[day.weekday()]
    out = {}
    for sec in cfg["sections"]:
        items = []
        for c in kid["chores"].get(sec["id"], []):
            if "days" in c and wd not in c["days"]:
                continue
            b = c.get("bonus", False)
            is_bonus = b is True or (isinstance(b, list) and wd in b)
            items.append({"id": sec["id"] + ":" + slug(c["name"]), "name": c["name"], "bonus": is_bonus})
        out[sec["id"]] = items
    return out


def parse_date(s):
    if not s:
        return date.today()
    return datetime.strptime(s, "%Y-%m-%d").date()


def day_state(d):
    cfg = load_config()
    hist = load_history().get(d.isoformat(), {})
    kids = []
    for kid in cfg["kids"]:
        done = set(hist.get(kid["id"], []))
        per = chores_for(cfg, kid, d)
        sections = []
        for sec in cfg["sections"]:
            items = [dict(c, done=c["id"] in done) for c in per[sec["id"]]]
            sections.append({"id": sec["id"], "name": sec["name"], "icon": sec.get("icon", ""), "chores": items})
        kids.append({"id": kid["id"], "name": kid["name"], "color": kid.get("color", "#2f6fde"), "sections": sections})
    return {
        "date": d.isoformat(),
        "today": date.today().isoformat(),
        "now": datetime.now().strftime("%H:%M"),
        "sectionStarts": {s["id"]: s.get("starts", "00:00") for s in cfg["sections"]},
        "kids": kids,
    }


def history_summary(n):
    cfg = load_config()
    hist = load_history()
    today = date.today()
    first = min([date.fromisoformat(k) for k in hist] + [today])  # don't list days before the chart existed
    rows = []
    for i in range(n):
        d = today - timedelta(days=i)
        if d < first:
            break
        rec = hist.get(d.isoformat(), {})
        kids = {}
        for kid in cfg["kids"]:
            done = set(rec.get(kid["id"], []))
            req = bon = req_done = bon_done = 0
            for items in chores_for(cfg, kid, d).values():
                for c in items:
                    if c["bonus"]:
                        bon += 1
                        bon_done += c["id"] in done
                    else:
                        req += 1
                        req_done += c["id"] in done
            kids[kid["id"]] = {"done": req_done, "total": req, "bonusDone": bon_done, "bonusTotal": bon}
        rows.append({"date": d.isoformat(), "kids": kids})
    return {"kids": [{"id": k["id"], "name": k["name"], "color": k.get("color")} for k in cfg["kids"]], "days": rows}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the journal quiet

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/api/day":
                return self.send_json(day_state(parse_date(q.get("date", [""])[0])))
            if url.path == "/api/history":
                return self.send_json(history_summary(min(int(q.get("days", ["14"])[0]), 366)))
        except Exception as e:  # bad date, broken chores.json, etc.
            return self.send_json({"error": str(e)}, 400)

        name = "index.html" if url.path in ("/", "/index.html") else url.path.lstrip("/")
        path = os.path.normpath(os.path.join(STATIC_DIR, name))
        if not path.startswith(STATIC_DIR) or not os.path.isfile(path):
            self.send_error(404)
            return
        ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
                 ".svg": "image/svg+xml", ".png": "image/png"}.get(os.path.splitext(path)[1], "application/octet-stream")
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/toggle":
            self.send_error(404)
            return
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            d = parse_date(data.get("date"))
            if d > date.today():
                return self.send_json({"error": "Can't check off future days"}, 400)
            kid_id, chore_id = data["kid"], data["chore"]
            cfg = load_config()
            kid = next(k for k in cfg["kids"] if k["id"] == kid_id)
            valid = {c["id"] for items in chores_for(cfg, kid, d).values() for c in items}
            if chore_id not in valid:
                return self.send_json({"error": "Unknown chore"}, 400)
            with lock:
                hist = load_history()
                done = hist.setdefault(d.isoformat(), {}).setdefault(kid_id, [])
                if chore_id in done:
                    done.remove(chore_id)
                else:
                    done.append(chore_id)
                save_history(hist)
            return self.send_json({"ok": True, "done": chore_id in done})
        except Exception as e:
            return self.send_json({"error": str(e)}, 400)


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    load_config()  # fail fast if chores.json has a typo
    print(f"Chore Chart running on http://localhost:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
