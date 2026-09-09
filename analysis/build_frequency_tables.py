"""Census + MCMIS crash file -> DOT-recordable crash rate per power-unit-year by segment, with a Poisson/NB GLM.
This is the script that replaces loss_cost.claim_frequency_per_unit_year (x crash_to_claim_ratio) and the
authority_age / fleet_size / venue relativities in config/rates.yaml with ESTIMATED values.

Inputs (download first — see docs/SOURCES.md):
  data/raw/census.csv      FMCSA Motor Carrier Census file
  data/raw/crash.csv       MCMIS crash file(s), 2-3 years concatenated
Column names differ between releases -> map them in COLS below. VERIFY every mapping against the file header.

Run: python -m analysis.build_frequency_tables --years 3
"""
import argparse, os, sys
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, DERIVED = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "data", "derived")

COLS = {  # VERIFY against actual headers
    "census": {"dot": "DOT_NUMBER", "state": "PHY_STATE", "units": "NBR_POWER_UNIT", "drivers": "DRIVER_TOTAL",
               "op": "CARRIER_OPERATION", "add_date": "ADD_DATE", "mcs150_date": "MCS150_DATE",
               "mileage": "MCS150_MILEAGE", "hm": "HM_FLAG", "pc": "PC_FLAG",
               "for_hire_flag": "AUTHORIZED_FOR_HIRE",   # may not exist; if absent we use CLASSDEF / operation class columns
               "cargo_genfreight": "CRGO_GENFREIGHT", "cargo_household": "CRGO_HOUSEHOLD", "cargo_liquids": "CRGO_LIQGAS",
               "cargo_motorveh": "CRGO_MOTOVEH"},
    "crash":  {"dot": "DOT_NUMBER", "date": "REPORT_DATE", "state": "REPORT_STATE", "fatal": "FATALITIES",
               "inj": "INJURIES", "tow": "TOW_AWAY"},
}

def load_census():
    c = COLS["census"]
    df = pd.read_csv(os.path.join(RAW, "census.csv"), low_memory=False, encoding_errors="ignore")
    df = df.rename(columns={v: k for k, v in c.items() if v in df.columns})
    df["units"] = pd.to_numeric(df["units"], errors="coerce")
    df = df[(df["units"] >= 1) & (df["units"] <= 5)]
    if "hm" in df: df = df[df["hm"].astype(str).str.upper() != "Y"]
    if "pc" in df: df = df[df["pc"].astype(str).str.upper() != "Y"]
    if "op" in df: df = df[df["op"].astype(str).str.upper().str.startswith("A")]   # 'A' = interstate in census; VERIFY code
    if "for_hire_flag" in df: df = df[df["for_hire_flag"].astype(str).str.upper().isin(["Y", "1", "TRUE"])]
    df["add_date"] = pd.to_datetime(df["add_date"], errors="coerce")
    return df

def load_crashes(years):
    c = COLS["crash"]
    files = [f for f in os.listdir(RAW) if f.startswith("crash") and f.endswith(".csv")]
    df = pd.concat([pd.read_csv(os.path.join(RAW, f), low_memory=False, encoding_errors="ignore") for f in files])
    df = df.rename(columns={v: k for k, v in c.items() if v in df.columns})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    cutoff = df["date"].max() - pd.DateOffset(years=years)
    df = df[df["date"] > cutoff]
    for k in ("fatal", "inj", "tow"): df[k] = pd.to_numeric(df.get(k), errors="coerce").fillna(0)
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
    # Poisson GLM with log(exposure) offset -> multiplicative relativities
    try:
        import statsmodels.formula.api as smf
        m = smf.glm("crashes ~ C(fleet) + C(auth_bucket) + C(state)", data=df[df["exposure"] > 0],
                    family=__import__("statsmodels.api", fromlist=["families"]).families.NegativeBinomial(),
                    offset=np.log(df.loc[df["exposure"] > 0, "exposure"])).fit()
        rel = np.exp(m.params).rename("relativity").to_frame(); rel["p"] = m.pvalues
        rel.to_csv(os.path.join(DERIVED, "glm_relativities.csv")); print(rel.to_string())
        print("\nPaste the fleet / auth_bucket / state relativities into config/rates.yaml and change their tag to [E].")
    except ImportError:
        print("statsmodels not installed: pip install statsmodels  (segment table above is still valid)")

if __name__ == "__main__":
    main()
