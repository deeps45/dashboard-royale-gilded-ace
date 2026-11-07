# Dashboard Royale — Gilded Ace floor review

TAMU Datathon “Dashboard Royale” submission. The casino is fictional and the data is synthetic.

- **Live dashboard:** https://deeps45.github.io/dashboard-royale-gilded-ace/
- [Write-up (≤400 words)](WRITEUP.md) · [Claims & evidence + AI disclosure](APPENDIX.md) · [Video script](VIDEO_SCRIPT.md)

## Reproduce

```sh
git clone --depth 1 https://github.com/tamu-datathon-org/dashboard-royale.git data-src
cp -R data-src/data .            # challenge data (not redistributed here)
python -m venv .venv && . .venv/bin/activate
pip install duckdb pandas pyarrow numpy scikit-learn
python analysis/q1_machines.py   # luck z-scores, GM bottom 10
python analysis/q1b.py           # M-1158 timeline, zone demand
python analysis/q2.py            # walkways, events, property trends
python analysis/q345.py          # downtime, staffing, players, comps
python analysis/q5b.py           # comp redemption detail
python analysis/q5c.py           # comp price change date, downtime cost
python analysis/model.py         # first forecast version
python analysis/model2.py        # CV model selection, interval, July forecast
python analysis/hit_audit.py     # hit-frequency leak test
python analysis/robustness.py    # placebo + calibration stress tests
python analysis/export.py        # builds docs/data.json for the dashboard
python analysis/verify.py        # 21 assertions; exits 1 on any mismatch
cd docs && python -m http.server # open http://localhost:8000
```

The dashboard is one static page (`docs/index.html`, Plotly). It recomputes every metric in the browser from `docs/data.json` for whatever period, zone, bank or guest group you select.
