# Luck, Location, or a Leak? — The Gilded Ace floor review

**Dashboard:** https://deeps45.github.io/dashboard-royale-gilded-ace/

**Verdict: don't replace the bottom 10.** Nine sit in the Back Forty, the quietest zone; five are 5%-hold games that earn less per dollar by design. None draws less play than its zone neighbours, and all ten make money after lease, service and power costs. A July lease would need +$211/day of extra theo just to repay itself; the one real swap (M-1120 → M-5076) added $9.

**Luck.** Exact luck scores (from `sum_bet_squared × payout_multiplier_variance`) have SD 1.09 across 310 machines, as pure luck predicts, and don't persist (r = 0.11).

**Leak.** **M-1158** fails twice: payouts beyond luck (z = −4.6) and a **38.6% hit rate vs 31.5% configured, every month**, in the meters (z = +124) *and* in carded sessions (z = +103). An hourly Tiger Data monitor flags it after 10 hours. Likely a paytable/records mismatch (~$73k a year): grounds to inspect, not accuse.

**Location.** When the Back Forty walkway closed, door counters fell 30% while the detour zone rose 14%, and play fell 29%. Back Forty coin-in tracks entries one-for-one (elasticity 1.03). June's 4% dip matches an 11% year-over-year fall in Las Vegas visitors.

**Players.** Card holders wagered $163.8M and lost $15.6M; the top 10% generate 66% of theo.

**Other leaks.** Downtime is small (99.6% availability) and mostly Ridgeline; April–May tech vacancies tripled waits. **On May 1 comp point prices fell 53%.** The visible cost barely moved, but the 156M points members hold became worth $7.6M instead of $3.5M: **+$4.1M exposure**. Heavy losers (80% of tracked losses) didn't gain; the increase went to everyone else.

**Model.** Six daily coin-in forecasters were compared by rolling-origin CV inside Jan–Apr; gradient boosting won and was scored once on May–Jun: MAE **$52.5k vs $218k** for the flat-mean baseline. Locals Week's lift sat inside its noise and below cost, so we fund no promotion.

**Plan: $15,100. Keep $84,900.**

| Action | Cost | Expected effect | Measure |
|---|---:|---|---|
| Inspect M-1158 + 2 lowest-z | $3,600 | ~$200/day recovered | Hit rate back to 31.5% |
| Back Forty signs | $7,500 | +5% entries (0–10%) ≈ $14k theo | Counters + diff-in-diff |
| Randomized comp pilot | $4,000 | ~$1.5k/month; decides the $4.1M exposure | Comp ÷ theo; heavy-loser visits as guardrail |

Rejected: replacements, relocation (no zone is full), preventive maintenance, extra technician, promotions.
