"""Hour-by-hour cumulative hit-rate z for the first week: M-1158 vs the envelope of all other machines.
Runs against the Tiger service loaded by tiger/run.py and adds 'alarm' to analysis/tiger.json."""
import os, json, psycopg
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
q = """
with c as (
  select h.machine_id, h.ts, g.hit_probability p, sum(h.hits) over w ch, sum(h.spins) over w cs
  from meter_hour h join machine_dim m using(machine_id) join game_math g using(config_id)
  where h.ts < timestamptz '2025-01-08 14:00+00'
  window w as (partition by h.machine_id order by h.ts rows unbounded preceding))
, z as (select machine_id, ts, (ch - p * cs) / sqrt(p * (1 - p) * cs) z from c where cs > 0)
select (ts at time zone 'America/Los_Angeles')::text t,
  max(z) filter (where machine_id = 'M-1158') m1158,
  max(z) filter (where machine_id <> 'M-1158') hi, min(z) filter (where machine_id <> 'M-1158') lo
from z group by ts order by ts"""
with psycopg.connect(os.environ['TIGER_URL']) as c:
    rows = c.execute(q).fetchall()
    shortfall = c.execute("""select sum(coin_in_cents - payout_cents) / 100.0 from meter_hour where machine_id = 'M-1158'""").fetchone()[0]
T = json.load(open('analysis/tiger.json'))
T['alarm'] = {'t': [r[0][:16] for r in rows], 'm1158': [None if r[1] is None else round(float(r[1]), 2) for r in rows],
              'hi': [round(float(r[2]), 2) for r in rows], 'lo': [round(float(r[3]), 2) for r in rows]}
T['early_warning']['m1158_coin_in_at_alarm'] = float(T['early_warning']['m1158_coin_in_at_alarm'])
T['m1158_house_win_h1'] = float(shortfall)
json.dump(T, open('analysis/tiger.json', 'w'), indent=1)
print(len(rows), 'hours; M-1158 house win H1', shortfall)
