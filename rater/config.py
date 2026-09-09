import json, os, yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT, "config")
DATA_DIR = os.path.join(ROOT, "data")

def _load_dotenv(path=os.path.join(ROOT, ".env")):
    """Load KEY=VALUE lines from .env into os.environ. Real env vars take precedence."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:  # -sig strips the BOM Notepad/PowerShell may write
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))

_load_dotenv()

def _load_yaml(name):
    with open(os.path.join(CONFIG_DIR, name)) as f:
        return yaml.safe_load(f)

def rates():   return _load_yaml("rates.yaml")
def rules():   return _load_yaml("rules.yaml")["rules"]
def schema():
    with open(os.path.join(CONFIG_DIR, "schema.json")) as f:
        return json.load(f)
