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
python data-src/scripts/verify_data.py && python data-src/scripts/verify_semantics.py  # organizer integrity checks (optional)
python analysis/q1_machines.py   # luck z-scores, GM bottom 10
python analysis/q1b.py           # M-1158 timeline, zone demand
python analysis/q2.py            # walkways, events, property trends
python analysis/q345.py          # downtime, staffing, players, comps
python analysis/q5b.py           # comp redemption detail
python analysis/q5c.py           # comp price change date, downtime cost
python analysis/model.py         # first forecast version
python analysis/model2.py        # CV model selection, interval, July forecast
python analysis/model3.py        # 12-candidate robustness search + block-bootstrap CIs
python analysis/hit_audit.py     # hit-frequency leak test
python analysis/robustness.py    # placebo + calibration stress tests
python analysis/deep.py          # contribution, traffic counters, real sources, sessions audit, comp liability
python analysis/export.py        # builds docs/data.json for the dashboard
python analysis/verify.py        # 37 assertions (4 need analysis/tiger.json); exits 1 on any mismatch
cd docs && python -m http.server # open http://localhost:8000
```

### Tiger Data (TimescaleDB) live leak monitor (optional)

Put `TIGER_URL=postgres://...` (a Tiger Cloud service) in `.env`, then:

```sh
pip install "psycopg[binary]" python-dotenv
python tiger/run.py            # hypertables, columnstore, continuous aggregates, benchmark, early-warning alarm
python tiger/alarm_series.py   # hour-by-hour alarm curve for the dashboard
python analysis/export.py      # adds the Tiger results to docs/data.json
```

1,321,908 hourly meter rows load into a hypertable. Compression takes storage from 158.8 MB to 32.0 MB (−80%), and the continuous aggregate answers the leak monitor 32× faster (2,006 → 62 ms server time). An hourly |z| ≥ 5 alarm flags M-1158 after 10 hours of play, with zero false alarms on the other 309 machines.
```

The dashboard is one static page (`docs/index.html`, Plotly). It recomputes every metric in the browser from `docs/data.json` for whatever period, zone, bank or guest group you select.
