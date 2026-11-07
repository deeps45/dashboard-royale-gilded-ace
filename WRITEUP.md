# Luck, Location, or a Leak? — The Gilded Ace floor review

**Dashboard:** https://deeps45.github.io/dashboard-royale-gilded-ace/

**Verdict: don't replace the bottom 10.** Nine of the ten sit in the Back Forty, the lowest-traffic zone, and five are 5%-hold games that earn less per dollar played by design. Judged fairly, by coin-in per day against their own zone's median, **none** draws less play than its neighbours. A same-slot swap (M-1120 → M-5076) already failed.

**Luck.** We compute each machine's exact luck standard deviation from `sum_bet_squared × payout_multiplier_variance`. The luck scores (z) across 310 machines have SD 1.09, which matches pure luck. One machine stands out: **M-1158** (z = −4.6, 3.0% hold vs 10% configured). A second, independent test explains why: it pays out on **38.6% of spins vs 31.5% configured, in every month (hit-rate z = +124)**, while every other machine is within ±3. Its payout table likely doesn't match its records, which costs about $73k a year. That's a reason to inspect, not an accusation. Any operator can run this audit monthly on meter data.

**Location.** When the Back Forty walkway closed (Mar 3 – Apr 7), Back Forty demand fell 25% while the rest of the floor rose 6%. Demand there follows access.

**Other leaks.** Downtime is small (99.6% availability, about $93k theo lost) and mostly on Ridgeline machines, which fault 3.7× as often as Halcyon. On **May 1 the comp point price was cut 53%** overnight. Comp cost per $ of theo rose from 0.78% to 0.86%, and play did not.

**Players.** Card holders wagered $163.8M and lost $15.6M; the top 10% generate 66% of theo. Nothing targets heavy losers.

**Model.** We forecast daily floor coin-in, training on Jan–Apr and testing on May–Jun with only pre-announced events. MAE: flat-mean baseline $218k, **ridge $54k (−75%)**. The June promotion's lift was inside the model's noise and below its cost, so we fund no promotion. It also serves as the counterfactual for July.

**Plan: $15,100. Keep $84,900.**

| Action | Cost | Expected effect | Measure |
|---|---:|---|---|
| Inspect M-1158 + 2 lowest-z | $3,600 | ~$200/day recovered | Hit rate back to 31.5% |
| Back Forty signs | $7,500 | +5% (0–10%) ≈ $14k theo | Diff-in-diff vs floor |
| Randomized comp pilot | $4,000 | ~$1.5k/month saved | Comp ÷ theo, visits |

Rejected: the GM's replacements ($33.8k+, no gain), preventive maintenance (needs ≥42% fewer faults), an extra technician, and promotions.
