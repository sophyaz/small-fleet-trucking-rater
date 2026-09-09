# Walkthrough deck — 8 slides

1. **The system in one picture** — pipeline diagram: submission → ingest → enrich (FMCSA / vPIC, cache-first) → features → rules → loss cost → price/refer/decline + breakdown.
2. **Scope** — what's insured, who, what's declined by appetite, the three-way decision.
3. **Data** — the SOURCES table; census × crash = rate with a denominator; what I distrusted.
4. **Loss cost** — crash rate by segment (table from build_frequency_tables), crash→claim, severity mixture, limited mean, trend. The base loss cost per unit-year.
5. **Relativities and credibility** — the manual page; Z curve; why a 1-truck crash is a surcharge not a decline.
6. **Rules** — D/R table with counts on the census draw; decline rate; what the book looks like (premium distribution).
7. **Sensitivity and validation** — tornado; ILF mixture vs lognormal; backtest; portfolio 1-in-200 and ROC.
8. **Where it's wrong, what to watch, roadmap.**

Live demo: `python -m rater.book samples/submissions_real` then `python -m rater their_carrier.json`.
