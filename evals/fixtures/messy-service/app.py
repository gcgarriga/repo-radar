import json
import os
import sqlite3
import urllib.request


DB = sqlite3.connect("data.db")
FLAGS = {"send_email": True, "debug": False, "retry": 3}


def run(x=None, y=None, z=None):
    if x is None:
        x = os.environ.get("INPUT", "users.json")
    rows = json.loads(open(x).read())
    out = []
    for r in rows:
        if "email" in r:
            u = r["email"].lower()
        elif "user" in r:
            u = r["user"]
        else:
            u = "unknown"
        DB.execute("insert into users values (?, ?, ?)", (u, str(r), z))
        if FLAGS["send_email"]:
            try:
                urllib.request.urlopen("https://example.invalid/" + u, timeout=1)
            except Exception:
                pass
        out.append({"id": u, "raw": r, "ok": True})
    open(y or "out.json", "w").write(json.dumps(out))
    return out


if __name__ == "__main__":
    print(run())
