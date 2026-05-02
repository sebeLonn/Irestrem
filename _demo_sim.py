"""
Demo simulator — sends rotating attention statuses for 5 fake students.
Run alongside the real server so the teacher dashboard has something to show.
"""
import json, time, math, urllib.request, random

SERVER = "http://localhost:8765"

STUDENTS = [
    {"name": "Alice Johnson",  "base": "present"},
    {"name": "Bob Smith",      "base": "looking_away"},
    {"name": "Charlie Davis",  "base": "absent"},
    {"name": "Diana Prince",   "base": "present"},
    {"name": "Ethan Hunt",     "base": "looking_away"},
]

STATUS_CYCLE = {
    "present":      ["present",      "present",      "present",      "looking_away"],
    "looking_away": ["looking_away", "present",      "looking_away", "absent"],
    "absent":       ["absent",       "absent",       "looking_away", "absent"],
}

scores = {s["name"]: random.uniform(0.5, 0.99) for s in STUDENTS}
away   = {s["name"]: 0.0 for s in STUDENTS}
tick   = 0

print("Demo simulator running — Ctrl+C to stop.")

while True:
    tick += 1
    for s in STUDENTS:
        name  = s["name"]
        cycle = STATUS_CYCLE[s["base"]]
        status = cycle[tick % len(cycle)]

        if status == "present":
            scores[name] = min(1.0, scores[name] + random.uniform(0.01, 0.03))
            away[name]   = 0.0
        else:
            scores[name] = max(0.1, scores[name] - random.uniform(0.01, 0.04))
            away[name]  += 2.0

        payload = json.dumps({
            "name":            name,
            "status":          status,
            "attention_score": round(scores[name], 2),
            "away_duration_s": round(away[name], 1),
        }).encode()

        try:
            req = urllib.request.Request(
                f"{SERVER}/update",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception as e:
            print(f"  send error: {e}")

    time.sleep(2)
