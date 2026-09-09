"""Evaluate decline / refer rules from config/rules.yaml over a feature dict."""
from .config import rules as load_rules

def _cmp(f, cond):
    if "all" in cond: return all(_cmp(f, c) for c in cond["all"])
    if "any" in cond: return any(_cmp(f, c) for c in cond["any"])
    v = f.get(cond["field"]); op = cond["op"]; t = cond.get("value")
    if v is None: return False
    try:
        if op == "eq": return v == t
        if op == "neq": return v != t
        if op == "gt": return v > t
        if op == "gte": return v >= t
        if op == "lt": return v < t
        if op == "lte": return v <= t
        if op == "in": return v in t
        if op == "not_in": return v not in t
        if op == "between": return t[0] <= v <= t[1]
        if op == "not_between": return not (t[0] <= v <= t[1])
    except TypeError:
        return False
    raise ValueError(f"unknown op {op}")

def evaluate(features: dict, rule_list=None) -> dict:
    rule_list = rule_list or load_rules()
    fired = [{"id": r["id"], "action": r["action"], "reason": r["reason"]} for r in rule_list if _cmp(features, r["when"])]
    if any(r["action"] == "decline" for r in fired): decision = "decline"
    elif any(r["action"] == "refer" for r in fired): decision = "refer"
    else: decision = "price"
    return {"decision": decision, "rules_fired": fired}
