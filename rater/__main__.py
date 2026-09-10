"""python -m rater path/to/submission.json  -> pretty-printed pricing result (never a traceback)."""
import json, sys
from .price import price

def main(argv):
    if len(argv) < 2:
        print(json.dumps({"decision": "error", "error": "usage: python -m rater path/to/submission.json"}))
        return 2
    path = argv[1]
    try:
        with open(path, encoding="utf-8-sig") as f:
            sub = json.load(f)
    except Exception as e:
        print(json.dumps({"submission_id": path, "decision": "error", "premium": None, "rules_fired": [],
                          "error": f"unreadable json: {e}"}, indent=2))
        return 1
    r = price(sub); r.pop("features", None)
    print(json.dumps(r, indent=2, default=str))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
