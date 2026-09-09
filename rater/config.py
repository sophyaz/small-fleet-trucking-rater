import json, os, yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT, "config")
DATA_DIR = os.path.join(ROOT, "data")

def _load_yaml(name):
    with open(os.path.join(CONFIG_DIR, name)) as f:
        return yaml.safe_load(f)

def rates():   return _load_yaml("rates.yaml")
def rules():   return _load_yaml("rules.yaml")["rules"]
def schema():
    with open(os.path.join(CONFIG_DIR, "schema.json")) as f:
        return json.load(f)
