"""Assertion suite: every headline number in the dashboard/write-up is recomputed from raw tables and checked.
Run: python analysis/verify.py   (exit code 1 on any failure)"""
import duckdb, json, sys, math
con=duckdb.connect(); v=lambda s: float(con.sql(s).fetchall()[0][0]); ok=[]; bad=[]
def check(name, got, lo, hi):
    (ok if lo<=got<=hi else bad).append(f"{'PASS' if lo<=got<=hi else 'FAIL'}  {name}: {got:,.4g} (expected {lo:,.4g}–{hi:,.4g})")
P="'data/1_prepared_views/prepared_daily_view.parquet'"; MD="'data/2_machine_decision/machine_day.parquet'"; G="'data/2_machine_decision/game_math.parquet'"
# money integrity
check('machine_day coin-in == prepared view coin-in ($)', abs(v(f"select sum(coin_in_cents)/100 from {MD}")-v(f"select sum(coin_in_usd) from {P}")),0,1)
check('house win == coin-in − payout (cents, all rows)', v(f"select sum(abs(house_win_cents-(coin_in_cents-payout_cents))) from {MD}"),0,0)
check('property_day coin-in == machine sum ($)', abs(v("select sum(coin_in_usd) from 'data/1_prepared_views/property_day.parquet'")-v(f"select sum(coin_in_usd) from {P}")),0,5)
# Q1
check('GM bottom-10 in Back Forty', v(f"select count(*) from (select machine_id, any_value(zone_name) z from {P} where location_id is not null group by 1 order by sum(house_win_usd) limit 10) where z='Back Forty'"),9,9)
z=v(f"select (sum(house_win_cents)-sum(theo_cents))/sqrt(sum(sum_bet_squared*payout_multiplier_variance)) from {MD} join {G} using(config_id) where machine_id='M-1158'")
check('M-1158 luck z', z,-4.6,-4.5)
hz=v(f"select (sum(payout_positive_spins)-any_value(hit_probability)::double*sum(paid_spins))/sqrt(any_value(hit_probability)::double*(1-any_value(hit_probability)::double)*sum(paid_spins)) from {MD} join {G} using(config_id) where machine_id='M-1158'")
check('M-1158 hit-rate z', hz,124,124.5)
R=json.load(open('analysis/robustness.json'))
check('Hit z SD excluding M-1158 (calibration)', R['hit']['sd_excl_1158'],0.85,1.15)
check('Luck z SD (calibration)', R['luck']['sd_all'],0.9,1.2)
check('Walkway DiD below every placebo', R['did']['real']-R['did']['placebo_min'],-9,0)
check('Weak-play machines in GM list (H1/Q1/Q2)', sum(w['weak_play'] for w in R['bottom10'].values()),0,0)
# Q3/Q5
check('Floor availability', v("select sum(available_seconds)/sum(scheduled_seconds) from "+MD+" where location_id is not null"),0.995,0.997)
check('Comp break date is May 1 (day index)', 1 if R['comp']['break_date']=='2025-05-01' else 0,1,1)
check('Comp points/$ before→after ratio', v("select (select -sum(points_delta)/sum(face_value_cents) from 'data/3_guests/loyalty_ledger.parquet' where event_type='redeem' and event_at_utc between '2025-05-01 13:00' and '2025-06-30') / (select -sum(points_delta)/sum(face_value_cents) from 'data/3_guests/loyalty_ledger.parquet' where event_type='redeem' and event_at_utc between '2025-04-01' and '2025-04-30 13:00')"),0.44,0.50)
check('Tracked player net ($M)', v("select sum(tracked_net_usd)/1e6 from 'data/1_prepared_views/player_period.parquet'"),-15.6,-15.55)
# model
M=json.load(open('analysis/model2.json'))
check('Selected model holdout MAE ($)', M['test'][M['selected']],50000,55000)
check('Baseline holdout MAE ($)', M['test']['Constant mean'],215000,221000)
check('Selected by CV = argmin CV', 1 if M['selected']==min(M['cv'],key=M['cv'].get) else 0,1,1)
# budget
A={r[0]:r[1:] for r in con.sql("select action_type_id, unit_cost_cents, recurring_cost_cents_per_day, lead_days, quantity_limit from 'data/2_machine_decision/action_catalog.parquet'").fetchall()}
plan={'A-INSPECT':3,'A-WAYFINDING':1,'A-COMP-PILOT':1}
cost=sum(q*(A[k][0]+A[k][1]*max(0,30-A[k][2]))/100 for k,q in plan.items())
check('Plan cost ($)',cost,15100,15100); check('Plan within quantity limits',sum(q>A[k][3] for k,q in plan.items()),0,0)
check('GM lease alternative ($)',10*(A['A-REPLACE-LEASE'][0]+A['A-REPLACE-LEASE'][1]*16)/100,33800,33800)
# deeper evidence (analysis/deep.py)
X=json.load(open('analysis/deep.json'))
check('GM bottom-10 (guide query, active rows) matches', v(f"select count(*) from (select machine_id from {P} where active group by 1 order by sum(house_win_usd) limit 10) where machine_id in ('M-5076','M-1158','M-1120','M-1118','M-1238','M-1181','M-1035','M-1179','M-1017','M-1265')"),10,10)
check('Machines with negative luck-neutral contribution', v(f"select count(*) from (select machine_id from {P} where location_id is not null group by 1 having sum(contribution_after_supplied_costs_usd-luck_residual_usd)<0)"),0,0)
check('July lease break-even theo/day ($)', X['contrib']['lease_breakeven_theo_day'],211,211.5)
check('Sessions hit-rate z, M-1158 (independent table)', X['sessions_audit']['m1158_z'],100,106)
check('Back Forty counter entries change during closure', X['traffic']['b40_chg'],-0.33,-0.27)
check('Back Forty coin-in elasticity to entries', X['traffic']['elasticity'],0.9,1.15)
check('Points liability economic exposure added ($M)', (X['liability']['econ_post']-X['liability']['econ_pre'])/1e6,3.9,4.3)
check('June coin-in vs weekday-mix expectation', X['season_gap']['2025-06'],-0.045,-0.035)
check('Own hold vs Missouri statewide hold (abs gap)', abs(X['context']['own_hold']-X['context']['mo_hold']),0,0.005)
M3=json.load(open('analysis/model3.json'))
check('Model v3: decision model unchanged (v2 holdout MAE)', M3['test']['Gradient boosting'],50000,55000)
check('Model v3: CV pick vs decision model, 95% CI of MAE gap includes 0', 1 if M3['ci']['diff'][0]<=0<=M3['ci']['diff'][1] else 0,1,1)
check('Model v3: baseline 95% CI lower bound above both models', 1 if M3['ci']['base'][0]>max(M3['ci']['v2'][1],M3['ci']['v3'][1]) else 0,1,1)
import os
if os.path.exists('analysis/tiger.json'):
    T=json.load(open('analysis/tiger.json'))
    check('Tiger Data: hourly rows, coin-in, spins, hits match local exactly', 1 if T['parity']['match'] else 0,1,1)
    check('Tiger Data: M-1158 hours of play to |z|>=5 alarm', T['early_warning']['m1158_hours_to_alarm'],1,24)
    check('Tiger Data: false alarms on other machines', T['early_warning']['false_alarms'],0,0)
    check('Tiger Data: continuous aggregate returns the same leak ranking', 1 if T['cagg_same_answer'] else 0,1,1)
D=json.load(open('docs/data.json'))
check('Dashboard data rows == machine-days on floor', len(D['md']['m']), v(f"select count(*) from {MD} where location_id is not null"), v(f"select count(*) from {MD} where location_id is not null"))
print('\n'.join(ok+bad)); print(f"\n{len(ok)} passed, {len(bad)} failed"); sys.exit(1 if bad else 0)
