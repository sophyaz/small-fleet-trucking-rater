"""python -m rater path/to/submission.json  -> pretty-printed pricing result"""
import json, sys
from .price import price
if __name__ == "__main__":
    with open(sys.argv[1]) as f: sub = json.load(f)
    r = price(sub); r.pop("features", None)
    print(json.dumps(r, indent=2, default=str))
