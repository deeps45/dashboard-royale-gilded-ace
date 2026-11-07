# Claims & Evidence Appendix

All code is in `analysis/`. Data: [tamu-datathon-org/dashboard-royale](https://github.com/tamu-datathon-org/dashboard-royale) release 0.9.0-draft. To reproduce, clone the challenge repo next to this one so that `data/` exists, then run `pip install duckdb pandas pyarrow scikit-learn` and run the scripts in the order below. The casino is fictional and its data is synthetic.

| # | Claim | Table / query → result | Alternative explanation tested | Limitation |
|---|---|---|---|---|
| 1 | The GM's bottom 10 are driven by location, not machine quality | `q1_machines.py`, `q1b.py`: bottom 10 by Σhouse_win; 9/10 are in Back Forty (M-1118 in High-Limit, retired Feb 24). Back Forty theo per machine-day is $280 vs $497 in Center Pit | The machines themselves are bad: their coin-in/day is 78–128% of the Back Forty median, and none is below 75% | Zone is taken from the last location in the period; only 4 moves in 6 months |
| 2 | Half of the bottom 10 are low-edge games by design | `game_math.configured_rtp` = 0.95 for 5 of them; theo/day is low because theo = coin-in × 5% | Players avoid them: occupancy and coin-in are at or above the zone median | We cannot test changing game settings (not in the catalogue) |
| 3 | Replacing a machine in the same slot doesn't help | `placements`, `machines`: M-1120 → M-5076 in B-38 on May 13; theo/day $143 → $153, both in the bottom 3 | The new machine needed ramp-up time: possible, but its coin-in/day already matched the zone median (106%) | One swap only |
| 4 | Luck is well calibrated | z = Σ(hw − theo) / √Σ(sum_bet_squared × payout_multiplier_variance); SD(z) = 1.09, mean −0.07, 1 machine with \|z\| > 3 | The variance model is wrong: an empirical SD near 1 supports it | Assumes independent spins |
| 5 | M-1158 needs an inspection | z = −4.57 (p ≈ 2e-6 one-sided; Bonferroni ×310 → 8e-4); hold 5.6% before Mar 10, −0.4% Mar 10–May, 6.1% in June; configured 10%. A fault repair was opened Mar 10 | Luck: rejected even after the multiple-test correction. A one-off jackpot: the shortfall is spread over 3 months, not one day | An unusual pattern is not proof of a fault or wrongdoing |
| 5b | M-1158 runs a different payout table than recorded | `hit_audit.py`: hit-rate z = (hits − p·spins)/√(p(1−p)·spins) = +124; 38.5–38.9% each month vs 31.5% configured; same-game peers 31.65%; next machine z +2.8 | Luck: impossible at z = 124. Meter error: payouts also exceed theo (luck z −4.6), so the tests agree. Repair-caused: the hit rate is high from January, before the Mar 10 repair | Which table is actually installed is unknown until inspected; not evidence of wrongdoing |
| 6 | Back Forty demand depends on access | Diff-in-diff around the W-ENT-B40 renovation closure (`floor_walkways`): Back Forty −24.6%, rest of floor +6.4%, so the diff-in-diff gap is −31.0 points | Seasonality or events: the rest of the floor saw the same calendar and rose | One closure; signs are a weaker intervention than a walkway |
| 7 | Downtime is small and Ridgeline-driven | `operations` fault_repair: 1,207 repairs, 5,021 machine-hours, $92.6k theo lost, $213k repairs; Ridgeline 7.2 faults/machine vs Northwind 3.0, Halcyon 1.9 | Ridgeline sits in busier zones: it has the most faults in every zone (e.g. Center Pit 8.9 vs 2.5) | Severity and parts are not observed |
| 8 | Overnight repairs wait twice as long | Average wait opened → work_started: Grave 1.96 h vs Day 0.90 h, Swing 0.85 h; roster shows 1 tech on grave | Fewer faults at night: there are fewer, but each waits longer | Small benefit: ~1 h × 50 faults × ~$5 theo/h per month |
| 9 | The comp point price halved on May 1 | `loyalty_ledger` redeem: −Σpoints / Σface by day: 12.3 (Apr 30) → 5.7 (May 1), all 10 items | A deliberate promotion: it isn't in `events`, and coin-in and visits did not rise (May–Jun coin-in in line with the weekday forecast) | Intent unknown, so we propose a pilot, not a unilateral reversal |
| 10 | Comp cost per theo rose | `property_day`: comp_cost ÷ theo 0.78% (Jan–Apr) → 0.86% (May–Jun), about $6.2k extra over 2 months. comp_cost is counted once (already inside cogs) | Higher volume: the ratio normalizes by theo | Small in dollars; the larger exposure is the points liability |
| 11 | Player outcomes | `player_period`: wagered $163.8M, paid back $148.2M, net −$15.6M; 14.4% of player-months ahead; top 1% = 23% of theo, top 10% = 66% | — | Carded play only; it does not match the machine meters, by design |
| 12 | The forecast beats the baseline | `model2.py`: 6 candidates compared by rolling-origin CV (five 14-day folds inside Jan–Apr). Gradient boosting chosen (CV $48.2k), holdout scored once: $52.5k vs constant mean $218k, weekday mean $68.7k, ridge $54.4k. Ridge + trend: CV $50.5k but holdout $74.9k | Selection bias: the test set is not used to choose. Leakage: only events announced before the cutoff | The 80% conformal interval covers 75% of holdout days; two-month test |
| 12b | Tech vacancies slowed repairs | `shift_roster` ⋈ `operations` (gaming date × shift): wait 4.9 h at 0 techs, 1.2–2.6 h at 1, 0.1–0.7 h at 2. Day shift 0.9 vs 1.7 planned in May | Busier days cause both: the dose-response holds within each shift | Observational; extra-tech ROI ≈ $1.2k/month vs $11.5k, so not funded |
| 12c | M-1158 is not a tampering case | `security_incidents`: 80 tampering reports, at most 3 per machine, none on M-1158 | — | Only reported incidents are recorded |
| 13 | Promotions don't pay here | Residual vs weekday forecast: Locals Week (out of sample) +$16k coin-in/day ≈ +$10.6k theo over 7 days, below the $15k cost | The tournament (in sample) showed +$61k, but it may coincide with other demand | Two promotions observed |

## Budget arithmetic

Cost = quantity × (unit + per-day × max(0, 30 − lead)). Inspect 3 × $1,200 = $3,600 (M-1158, M-1054, M-1210). Wayfinding 1 × $7,500. Comp pilot $4,000. **Total $15,100. Reserve $84,900.** For comparison, 10 leases = 10 × ($2,500 + 16 × $55) = $33,800, and 10 purchases = $220,000 (over budget).

Sensitivity: the signs break even at +2.6% Back Forty demand. Preventive maintenance ($9k) would need a ≥ 42% fault reduction on Ridgeline over 23 days. The inspections pay back if one fault worth ≥ $1.2k is found.

## AI-use disclosure

We used Claude (Anthropic, via Claude Code) to help write DuckDB/pandas analysis code, build the static Plotly dashboard, and draft this write-up and appendix. Every number was produced by the scripts in `analysis/` from the challenge data and checked by running them. The analytical choices (luck z-score, diff-in-diff, time-split holdout, action selection) were reviewed by the team.

## Robustness checks (`analysis/robustness.py`) and verification (`analysis/verify.py`)

| Finding | Attack | Result |
|---|---|---|
| Back Forty demand follows access | Placebo diff-in-diff on 80 fake 34-day closures | Real gap −31.0 pts; placebos +3.7% to +13.4% (p < 1/80) |
| Low earners are mostly unlucky | Correlation of each machine's luck z, Jan–Mar vs Apr–Jun | r = 0.11 (0.08 without M-1158): luck does not persist |
| Luck model is calibrated | SD of luck z across machines | 1.095 |
| Hit-frequency test is calibrated | SD of hit-rate z excluding M-1158 | 1.006, max \|z\| = 2.8 |
| M-1158 is not a short bad stretch | Hit-rate z month by month | Weakest month +47 |
| Comp change is a single break | Largest day-over-day change in points per $ | May 1 (−6.56); next largest 0.47 |
| The GM's raw ranking is unstable | Bottom 10 by raw house win in Q1 | 8 of 10 are new machines with 8 days on the floor; 0 weak-play machines in any window |

`python analysis/verify.py` re-derives 21 headline numbers from the raw tables (money integrity, Q1–Q5 figures, model metrics, budget arithmetic, dashboard data completeness) and exits non-zero on any mismatch. All 21 pass.
