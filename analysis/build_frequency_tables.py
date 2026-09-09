"""Census + MCMIS crash file -> DOT-recordable crash rate per power-unit-year by segment, with a Poisson/NB GLM.
This is the script that replaces loss_cost.claim_frequency_per_unit_year (x crash_to_claim_ratio) and the
authority_age / fleet_size / venue relativities in config/rates.yaml with ESTIMATED values.

Inputs (download first — see docs/SOURCES.md rows S3/S4):
  data/raw/census.csv        FMCSA "SMS Input - Motor Carrier Census Information" (data.transportation.gov kjg3-diqy)
  data/raw/crash_<year>.csv  FMCSA "Crash File" (data.transportation.gov aayw-vxb3), one calendar year per file
Column names differ between releases -> map them in COLS below. Mapped 2026-09-09 against the Socrata
resource-endpoint CSV export (lower-case field names). Value formats that matter:
  census: hm_flag / pc_flag / authorized_for_hire are the strings "true"/"false"; carrier_operation is
          A = interstate, B = intrastate hazmat, C = intrastate non-hazmat; add_date / mcs150_date are "DD-MON-YY".
  crash:  report_date is YYYYMMDD (read as int by pandas -> parse with an explicit format); tow_away is "Y"/"N";
          federal_recordable is "Y"/"N"; one row per CMV involved (report_number + report_seq_no).

Run: python -m analysis.build_frequency_tables --years 3
"""
import argparse, os, sys
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, DERIVED = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "data", "derived")

COLS = {  # verified against data/raw headers on 2026-09-09 (see docs/SOURCES.md S3/S4)
    "census": {"dot": "dot_number", "state": "phy_state", "units": "nbr_power_unit", "drivers": "driver_total",
               "op": "carrier_operation", "add_date": "add_date", "mcs150_date": "mcs150_date",
               "mileage": "mcs150_mileage", "hm": "hm_flag", "pc": "pc_flag",
               "for_hire_flag": "authorized_for_hire"},
               # The SMS census input carries no CRGO_* cargo columns; those live in the full "Company Census File"
               # (data.transportation.gov az4n-8mr2: crgo_genfreight, crgo_household, crgo_liqgas, crgo_motoveh).
    "crash":  {"dot": "dot_number", "date": "report_date", "state": "report_state", "fatal": "fatalities",
               "inj": "injuries", "tow": "tow_away", "recordable": "federal_recordable"},
}
TRUE_VALUES = {"Y", "TRUE", "1", "T"}

def load_census():
    c = COLS["census"]
    df = pd.read_csv(os.path.join(RAW, "census.csv"), low_memory=False, encoding_errors="ignore")
    df = df.rename(columns={v: k for k, v in c.items() if v in df.columns})
    df["units"] = pd.to_numeric(df["units"], errors="coerce")
    df = df[(df["units"] >= 1) & (df["units"] <= 5)]
    if "hm" in df: df = df[~df["hm"].astype(str).str.upper().isin(TRUE_VALUES)]
    if "pc" in df: df = df[~df["pc"].astype(str).str.upper().isin(TRUE_VALUES)]
    if "op" in df: df = df[df["op"].astype(str).str.upper().str.startswith("A")]   # A = interstate (B/C = intrastate)
    if "for_hire_flag" in df: df = df[df["for_hire_flag"].astype(str).str.upper().isin(TRUE_VALUES)]
    # add_date is "DD-MON-YY"; the explicit format applies the 69-99 -> 19xx rule so 1974-1976 does not become 2074-2076
    df["add_date"] = pd.to_datetime(df["add_date"], format="%d-%b-%y", errors="coerce")
    return df

def load_crashes(years):
    c = COLS["crash"]
    files = [f for f in os.listdir(RAW) if f.startswith("crash") and f.endswith(".csv")]
    df = pd.concat([pd.read_csv(os.path.join(RAW, f), low_memory=False, encoding_errors="ignore") for f in files])
    df = df.rename(columns={v: k for k, v in c.items() if v in df.columns})
    df["date"] = pd.to_datetime(df["date"].astype(str).str.slice(0, 8), format="%Y%m%d", errors="coerce")
    cutoff = df["date"].max() - pd.DateOffset(years=years)
    df = df[df["date"] > cutoff]
    if "recordable" in df: df = df[df["recordable"].astype(str).str.upper().isin(TRUE_VALUES)]   # DOT-recordable only
    for k in ("fatal", "inj"): df[k] = pd.to_numeric(df.get(k), errors="coerce").fillna(0)
    df["tow"] = df["tow"].astype(str).str.upper().isin(TRUE_VALUES).astype(int) if "tow" in df else 0
    return df, years

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--years", type=int, default=3); a = ap.parse_args()
    if not os.path.exists(os.path.join(RAW, "census.csv")):
        sys.exit("census.csv not found in data/raw — see docs/SOURCES.md and docs/CLAUDE_CODE_PROMPTS.md (Prompt 2)")
    cen = load_census(); cr, yrs = load_crashes(a.years)
    print(f"census segment carriers: {len(cen):,}; crashes in window: {len(cr):,}")
    agg = cr.groupby("dot").agg(crashes=("dot", "size"), fatal=("fatal", lambda s: (s > 0).sum()), inj=("inj", lambda s: (s > 0).sum())).reset_index()
    df = cen.merge(agg, on="dot", how="left").fillna({"crashes": 0, "fatal": 0, "inj": 0})
    now = pd.Timestamp.today()
    df["auth_age"] = (now - df["add_date"]).dt.days / 365.25
    df["auth_bucket"] = pd.cut(df["auth_age"], [-1, 1, 3, 200], labels=["<1y", "1-3y", "3y+"])
    df["fleet"] = np.where(df["units"] == 1, "1", "2-5")
    df["exposure"] = df["units"] * yrs
    # NOTE: carriers added within the window have less than `yrs` of exposure -> approximate: min(auth_age, yrs)
    df["exposure"] = df["units"] * np.minimum(df["auth_age"].clip(lower=0.1), yrs)
    tab = df.groupby(["fleet", "auth_bucket"], observed=True).agg(carriers=("dot", "size"), unit_years=("exposure", "sum"),
          crashes=("crashes", "sum"), fatal=("fatal", "sum"), inj=("inj", "sum")).reset_index()
    tab["crash_rate_per_unit_year"] = tab["crashes"] / tab["unit_years"]
    tab["rate_se"] = np.sqrt(tab["crashes"]) / tab["unit_years"]
    tab["fatal_share"] = tab["fatal"] / tab["crashes"]; tab["inj_share"] = tab["inj"] / tab["crashes"]
    os.makedirs(DERIVED, exist_ok=True)
    tab.to_csv(os.path.join(DERIVED, "crash_rate_by_segment.csv"), index=False); print(tab.to_string())
    st = df.groupby("state").agg(unit_years=("exposure", "sum"), crashes=("crashes", "sum"), fatal=("fatal", "sum"), inj=("inj", "sum")).reset_index()
    st["crash_rate"] = st["crashes"] / st["unit_years"]; st["fatal_share"] = st["fatal"] / st["crashes"]
    st.to_csv(os.path.join(DERIVED, "crash_rate_by_state.csv"), index=False)
    # Negative-binomial GLM with log(exposure) offset -> multiplicative relativities.
    # Reference levels = the manual's base segment (fleet 2-5, authority 3y+) and the state with the most unit-years,
    # so each coefficient is directly the factor that would go into rates.yaml and its SE is that factor's SE.
    # NB2 dispersion alpha is estimated from a Poisson fit by the Cameron-Trivedi auxiliary regression
    # ((y-mu)^2 - y)/mu = alpha*mu, instead of statsmodels' fixed default alpha=1.
    try:
        import statsmodels.api as sm, statsmodels.formula.api as smf
        ref_state = st.sort_values("unit_years", ascending=False)["state"].iloc[0]
        d = df[df["exposure"] > 0].copy(); d["auth_bucket"] = d["auth_bucket"].astype(str)
        terms = {f"C(fleet, Treatment(reference='2-5'))": "fleet", f"C(auth_bucket, Treatment(reference='3y+'))": "auth_bucket",
                 f"C(state, Treatment(reference='{ref_state}'))": "state"}
        formula = "crashes ~ " + " + ".join(terms)
        pois = smf.glm(formula, data=d, family=sm.families.Poisson(), offset=np.log(d["exposure"])).fit()
        mu = pois.fittedvalues; alpha = max(float(np.sum((d["crashes"] - mu) ** 2 - d["crashes"]) / np.sum(mu ** 2)), 1e-6)
        m = smf.glm(formula, data=d, family=sm.families.NegativeBinomial(alpha=alpha), offset=np.log(d["exposure"])).fit()
        rel = np.exp(m.params).rename("relativity").to_frame()
        rel["se_log"] = m.bse; rel["relativity_se"] = rel["relativity"] * m.bse   # delta method
        rel["p"] = m.pvalues
        rel.index = [__import__("functools").reduce(lambda s, kv: s.replace(kv[0], kv[1]), terms.items(), i) for i in rel.index]
        print(f"NB alpha (Cameron-Trivedi) = {alpha:.4f}; reference levels: fleet 2-5, auth 3y+, state {ref_state}; n = {len(d):,}")
        rel.to_csv(os.path.join(DERIVED, "glm_relativities.csv")); print(rel.to_string())
        print("\nPaste the fleet / auth_bucket / state relativities into config/rates.yaml and change their tag to [E].")
    except ImportError:
        print("statsmodels not installed: pip install statsmodels  (segment table above is still valid)")

if __name__ == "__main__":
    main()
