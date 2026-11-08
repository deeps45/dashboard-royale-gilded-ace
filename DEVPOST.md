# Devpost submission: copy and paste

## Project name (≤ 60 characters)
Luck, Location, or a Leak? The Gilded Ace Floor Review

## Elevator pitch (≤ 200 characters)
The GM wanted to replace 10 slot machines. Our dashboard shows 9 are victims of location, one is leaking ~$73k a year, and a live Tiger Data alarm would have caught it in 10 hours.

---

## About the project (Markdown, paste into "Project story")

## Inspiration
The Gilded Ace's general manager planned to replace the ten machines that earned the least in the first half of 2025. A machine can earn little for many reasons: bad luck, a quiet corner, downtime, or paying out differently than it should. Replacing it only helps if the machine itself is the problem. We wanted a dashboard that tests all three explanations, **luck, location, or a leak**, before anyone spends a dollar.

## What it does
An interactive floor review that takes a manager from question to decision:

- **Verdict in one screen.** Don't replace the bottom 10. Nine sit in Back Forty, the lowest-traffic zone. Five are 5%-hold games that earn less per dollar by design. None draws weak play for its zone, and all ten are profitable after lease, service and power costs. A July lease would need +$211/day of extra play just to repay itself, and the one real same-slot swap added $9/day.
- **Luck, measured exactly.** Each machine's luck score uses its own bet sizes and its game's payout variance. Across 310 machines the scores follow a normal curve (SD 1.09), and they don't persist from one half to the next (r = 0.11).
- **The leak.** A second, independent test checks how often each machine pays at all. **M-1158 pays on 38.6% of spins vs 31.5% configured, every month** (z = +124 in the meters, +103 in the separate player-tracking records). It costs about $200/day. That is a reason to inspect, not an accusation.
- **Location, proven by a natural experiment.** When Back Forty's walkway closed for renovation, door counts fell 30% and play fell 29% while the detour zone rose 14%. That is a −31 point gap, beyond all 80 placebo tests.
- **A hidden comp cost.** On May 1, every comp got 53% cheaper in points overnight. The monthly bill barely moved, but the 156M points members already hold went from $3.5M to **$7.6M** of potential cost.
- **A forecast that changes decisions.** Six models were compared by rolling-origin cross-validation inside Jan–Apr. The winner was scored once on May–Jun: MAE **$52.5k vs $218k** for the baseline (−76%), with bootstrap confidence intervals. It shows the promotion's lift was inside the noise, so we don't fund one, and it tells us which July days need the refilled tech shifts.
- **A priced plan within budget.** Spend **$15,100 and keep $84,900**: inspect three machines ($3,600), add Back Forty signage ($7,500), and run a randomized comp pilot ($4,000) with a guardrail so heavy losers are never encouraged to play more. Each action has a cost, an expected effect, an uncertainty range and a measurement plan, plus a link back to its evidence.

**Interactive by design:** a slot-machine entrance; jackpot meters whose digits roll as you change the period, zone, bank or guest group; an animated floor map that dims Back Forty in March; a "Call it" card game over the GM's ten machines; a "Pull the lever" simulator that shows the leak becoming undeniable; a click-any-machine profile; a guided **Judge tour** that performs the four judging tasks; and **Ask the Floor**, a Gemini analyst that answers from verified numbers and drives the dashboard.

## How we built it
- **Analysis:** Python, DuckDB and pandas over all challenge tables, including machine meters, sessions, the loyalty ledger, door counters, cost rules, and the real LVCVA, NOAA and Missouri benchmark data, used for context only.
- **Model:** scikit-learn, with rolling-origin CV for selection, a single holdout score, a conformal interval and a paired weekly block bootstrap. No future data: event flags only count events announced before the forecast date.
- **Tiger Data (TimescaleDB):** 1,321,908 hourly meter rows in a hypertable with columnstore compression (**158.8 MB → 32.0 MB, −80%**) and continuous aggregates by gaming day (**32× faster** leak monitor, identical answers). An hourly alarm query flags M-1158 **after 10 hours of play with zero false alarms** on 309 other machines.
- **Dashboard:** a single static page (HTML, CSS, JavaScript, Plotly.js) on GitHub Pages. Every metric is recomputed in the browser for any filter.
- **Ask the Floor:** Google Gemini with function calling, behind a Cloudflare Worker that keeps the key server-side, allowlists origins and models, rate-limits, and caches answers.
- **Trust:** `verify.py` re-derives 37 headline numbers from the raw tables and fails on any mismatch. The organizers' `verify_data.py` and `verify_semantics.py` also pass.

## Challenges we ran into
- **Separating bad luck from a broken machine.** A luck score alone can't, so we added the hit-frequency test, then confirmed it in a second, independent table.
- **Honest model selection.** A wider 12-model search found a model that scored better on the holdout, but cross-validation hadn't picked it. We kept the original model and reported the bootstrap interval instead of choosing by the test set.
- **A claim we had to retract.** We first said June's dip was just the weekday mix. Adjusting for weekdays showed June was really 4% low, in step with an 11% year-over-year drop in Las Vegas visitors, so we corrected it.
- **Shipping AI safely on a static site:** keeping the key secret, staying within free-tier limits, and stopping the model from inventing citations.

## Accomplishments that we're proud of
- An unexpected, reproducible finding: a meter-only audit any operator could run monthly, which would have caught M-1158 on day one.
- Every claim traces to a table, a result, a rival explanation we tested, and a limitation (26 claims in the appendix).
- A plan that keeps 85% of the budget, because the evidence says most of the GM's list isn't broken.

## What we learned
Raw totals mostly rank how long a machine has been on the floor and where it sits. Fair comparisons need exposure, availability and luck adjusted, and a finding is only convincing once you've tried to break it.

## What's next for Luck, Location, or a Leak?
Run the Tiger Data alarm live on streaming meters, add a formal sequential-testing boundary for continuous monitoring, and use the randomized comp pilot's result to decide the points price floor-wide.

---

## Built with
python, duckdb, pandas, numpy, scikit-learn, javascript, html5, css3, plotly.js, timescaledb, tiger-data, postgresql, google-gemini, cloudflare-workers, github-pages, playwright

## "Try it out" links
- Live dashboard: https://deeps45.github.io/dashboard-royale-gilded-ace/
- Code: https://github.com/deeps45/dashboard-royale-gilded-ace
- Write-up (400 words): https://github.com/deeps45/dashboard-royale-gilded-ace/blob/main/WRITEUP.md
- Claims & evidence appendix + AI-use disclosure: https://github.com/deeps45/dashboard-royale-gilded-ace/blob/main/APPENDIX.md

## Prize tracks to select
- Dashboard Royale (main challenge)
- Best Use of Tiger Data
- Best Use of Gemini API

## Notes for the form
- The casino is fictional and all of its data is synthetic (challenge release 0.9.0-draft).
- AI tools used: Claude (Anthropic, via Claude Code) for code and drafting; Google Gemini powers the in-app assistant. Full disclosure is in APPENDIX.md.
