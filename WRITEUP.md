# Luck, Location, or a Leak? — The Gilded Ace floor review

**Dashboard:** https://deeps45.github.io/dashboard-royale-gilded-ace/

**Verdict: don't replace the bottom 10.** Nine of the GM's ten lowest earners sit in the Back Forty, the floor's lowest-traffic zone. Five are low-edge games (5% hold) that earn less per dollar played *by design*. Measured fairly, by coin-in per day against their own zone's median, **none** of them draws less play than its neighbours. The swap has already been tried: M-1120 was replaced by M-5076 in the same slot (B-38), and the newcomer also landed in the bottom 10.

**Luck.** We compute each machine's exact luck standard deviation from `sum_bet_squared × payout_multiplier_variance` and score it as z = (house win − theo) / SD. Across 310 machines the z-scores have SD 1.09 and mean −0.07, which is what pure luck predicts. One machine stands out: **M-1158** (z = −4.6, 3.0% hold vs 10% configured). Its hold collapsed after a March 10 repair, and the result is still significant after a Bonferroni correction across all machines. That is a reason to inspect, not an accusation.

**Location.** The Back Forty walkway closure (Mar 3 – Apr 7) is a natural experiment. Back Forty demand fell 25% while the rest of the floor rose 6%, a −29-point difference-in-differences. Demand there follows access, not machines.

**Leaks elsewhere.** Downtime is small: 99.6% availability, about $93k of theo lost over six months, more than half of it on Ridgeline machines (7.2 faults per machine vs 1.9 for Halcyon in every zone). On **May 1 the comp point price fell 53%** (12.4 → 5.8 points per $1, on every item, overnight). Comp cost per $ of theo rose from 0.78% to 0.86%, and coin-in and visits did not rise.

**Players.** Card holders wagered $163.8M and lost $15.6M (9.5% hold vs 9.45% theo). 14% of player-months ended ahead. The top 10% of players generate 66% of theo. We propose no idea that pushes heavy losers to play more.

**Model.** We forecast daily floor coin-in, training on Jan–Apr and testing on May–Jun, using only events announced before May 1. MAE: constant-mean baseline $218k, weekday mean $69k, **ridge $54k (−75%)**. The model changes two decisions. Out of sample, the Locals Week promotion's lift (+$11k theo over 7 days) fell inside the model's noise and below the $15k promotion cost, so we skip promotions. And the forecast is the counterfactual for measuring July actions.

**Plan: $18,700 of $100,000. Keep $81,300.**

| Action | Cost | Expected effect (range) | Measure |
|---|---:|---|---|
| Inspect 6 machines with the lowest z (M-1158 first) | $7,200 | ~$6k/month if M-1158 is faulty; otherwise information | Inspection report; July z back within ±2 |
| New signs for Back Forty | $7,500 | +5% demand (0–10%) ≈ +$14k theo ($0–29k) | Diff-in-diff vs rest of floor, against the forecast |
| Comp pilot (50/50 randomized: 12.4 vs 5.8 points per $) | $4,000 | ~$1.5k/month saved on the treated half | Comp cost ÷ theo, visits, coin-in per player |

We rejected the GM's replacements ($33.8k leased / $220k bought, expected gain ≈ 0), preventive maintenance (breaks even only if faults fall ≥ 42%), an extra technician (~$250/month benefit), and a promotion weekend.
