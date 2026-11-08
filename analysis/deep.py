"""Deeper evidence: contribution after supplied costs, traffic counters, real-world context,
independent session-level hit audit, comp distribution, points liability, incidents, the B-38 swap.
Writes analysis/deep.json (consumed by export.py)."""
import duckdb, json, numpy as np, pandas as pd

c = duckdb.connect()
D = 'data/'
PDV = f"'{D}1_prepared_views/prepared_daily_view.parquet'"
c.sql(f"create view d as select * from {PDV} where location_id is not null")
out = {}

# 1. Machine contribution after supplied costs, luck-neutral (house win replaced by theo)
m = c.sql("""select machine_id, any_value(zone_name) zone, any_value(lease_class) lc, count(*) nd,
  sum(contribution_after_supplied_costs_usd) ctb,
  sum(contribution_after_supplied_costs_usd - luck_residual_usd)/count(*) cn_day,
  sum(theo_usd)/count(*) theo_day,
  sum(lease_cost_usd+service_cost_usd+power_cost_usd+repair_cost_usd)/count(*) cost_day
  from d group by 1""").df()
gm = c.sql(f"select machine_id from {PDV} where active group by 1 order by sum(house_win_usd) limit 10").df().machine_id.tolist()
g = m[m.machine_id.isin(gm)]
lease = c.sql(f"select unit_cost_cents/100 u, recurring_cost_cents_per_day/100 r, lead_days l from '{D}2_machine_decision/action_catalog.parquet' where action_type_id='A-REPLACE-LEASE'").fetchall()[0]
op_days = max(0, 30 - lease[2])
out['contrib'] = dict(
    machines_negative=int((m.cn_day < 0).sum()), min_cn_day=round(m.cn_day.min(), 1),
    gm_min=round(g.cn_day.min(), 1), gm_max=round(g.cn_day.max(), 1),
    gm=g[['machine_id', 'zone', 'lc', 'cn_day', 'theo_day', 'cost_day']].round(1).to_dict('records'),
    # theo uplift a July lease needs just to repay itself: (unit + per-day*op_days)/op_days
    lease_breakeven_theo_day=round((float(lease[0]) + float(lease[1]) * op_days) / op_days, 1),
    lease_op_days=op_days)
pm = c.sql(f"""select strftime(gaming_date,'%Y-%m') mo, sum(house_win_usd) hw, sum(pos_cash_usd-pos_cogs_usd) fnb,
  sum(machine_supplied_costs_usd) mc, sum(tech_labor_cost_usd) tech, sum(contribution_after_supplied_costs_usd) ctb,
  sum(contribution_after_supplied_costs_usd)/count(*) ctb_day
  from '{D}1_prepared_views/property_day.parquet' group by 1 order by 1""").df()
out['contrib_month'] = pm.round(0).to_dict('list')

# 2. Traffic counters (offline hours excluded; partial hours scaled by coverage)
t = c.sql(f"""select zone_id, cast(hour_start_local - interval 6 hour as date) gd, sum(entries_count) e,
  sum(coverage_minutes)/60.0 cv from '{D}4_context/zone_traffic_hourly.parquet'
  where counter_status <> 'offline' group by all""").df()
t['rate'] = t.e / t.cv * 24
t['gd'] = pd.to_datetime(t.gd)
CL0, CL1 = pd.Timestamp('2025-03-03'), pd.Timestamp('2025-04-07')
per = lambda s: np.where(s < CL0, 'pre', np.where(s < CL1, 'closed', 'post'))
t['per'] = per(t.gd)
tp = t.groupby(['zone_id', 'per']).rate.mean().unstack()
tp['chg'] = tp.closed / tp.pre - 1
z = c.sql("select zone_id, gaming_date gd, sum(coin_in_usd) ci, count(*) n from d group by all").df()
z['gd'] = pd.to_datetime(z.gd)
b = t[t.zone_id == 'Z-B40'].merge(z[z.zone_id == 'Z-B40'], on='gd')
b['cim'] = b.ci / b.n; b = b.sort_values('gd')
el = np.polyfit(np.log(b.rate), np.log(b.cim), 1)[0]
z['per'] = per(z.gd)
zc = z.groupby(['zone_id', 'per'])[['ci', 'n']].sum()
zc = (zc.ci / zc.n).unstack()
rest = t[t.zone_id != 'Z-B40'].groupby('gd').rate.sum().sort_index()
b40 = t[t.zone_id == 'Z-B40'].set_index('gd').rate.sort_index()
out['traffic'] = dict(
    b40_chg=round(tp.loc['Z-B40', 'chg'], 3), bar_chg=round(tp.loc['Z-BAR', 'chg'], 3),
    b40_ci_chg=round(zc.loc['Z-B40', 'closed'] / zc.loc['Z-B40', 'pre'] - 1, 3),
    elasticity=round(el, 2), corr=round(np.corrcoef(b.rate, b.cim)[0, 1], 3),
    zone_chg={k: round(v, 3) for k, v in tp.chg.items()},
    offline_hours=int(c.sql(f"select count(*) from '{D}4_context/zone_traffic_hourly.parquet' where counter_status='offline'").fetchall()[0][0]),
    days=[x.strftime('%Y-%m-%d') for x in b40.index], b40=b40.round(0).tolist(),
    rest=(rest.reindex(b40.index) / rest[rest.index < CL0].mean() * 100).round(1).tolist(),
    b40_idx=(b40 / b40[b40.index < CL0].mean() * 100).round(1).tolist(),
    scatter_rate=b.rate.round(0).tolist(), scatter_ci=b.cim.round(0).tolist())

# 3. Real-world context (context only: published after the window, never a forecast input)
R = f'{D}4_context/real_sources/'
v = c.sql(f"select month, mean_visitors_per_calendar_day mv, visitor_yoy_ratio yoy, convention_attendance conv from '{R}city_visitation_monthly.parquet' order by 1").df()
pdy = c.sql(f"select gaming_date gd, coin_in_usd ci, pos_cash_usd fnb from '{D}1_prepared_views/property_day.parquet'").df()
pdy['gd'] = pd.to_datetime(pdy.gd)
mo = pdy.groupby(pdy.gd.dt.strftime('%Y-%m')).agg(ci=('ci', 'mean'), fnb=('fnb', 'mean'))
w = c.sql(f"select source_date gd, tmax_c from '{R}weather_daily.parquet'").df()
w['gd'] = pd.to_datetime(w.gd)
x = pdy.merge(w, on='gd')
wd = x.gd.dt.dayofweek
x['r_ci'] = x.ci - x.groupby(wd).ci.transform('mean')
x['r_fnb'] = x.fnb - x.groupby(wd).fnb.transform('mean')
st = c.sql(f"select sum(agr_usd)::double, sum(handle_usd)::double from '{R}benchmark_state_monthly.parquet'").fetchall()[0]
own = c.sql(f"select sum(house_win_usd)/sum(coin_in_usd) from '{D}1_prepared_views/property_day.parquet'").fetchall()[0][0]
out['context'] = dict(
    months=v.month.tolist(), visitors=v.mv.round(0).tolist(), yoy=v.yoy.tolist(), conv=v.conv.tolist(),
    ci=mo.ci.round(0).tolist(), fnb=mo.fnb.round(0).tolist(),
    corr_ci_visitors=round(np.corrcoef(mo.ci, v.mv)[0, 1], 2),
    corr_tmax_ci=round(np.corrcoef(x.r_ci, x.tmax_c)[0, 1], 3), corr_tmax_fnb=round(np.corrcoef(x.r_fnb, x.tmax_c)[0, 1], 3),
    mo_hold=round(st[0] / st[1], 4), own_hold=round(float(own), 4))

# 4. Independent hit-rate audit from carded sessions (a different table from the meters)
s = c.sql(f"""select s.machine_id, g.hit_probability p, sum(paid_spins) sp, sum(payout_positive_spins) hp
  from '{D}3_guests/sessions.parquet' s join '{D}2_machine_decision/game_math.parquet' g using(config_id) group by all""").df()
s['z'] = (s.hp - s.p * s.sp) / np.sqrt(s.p * (1 - s.p) * s.sp)
r = s[s.machine_id == 'M-1158'].iloc[0]
o = s[s.machine_id != 'M-1158']
out['sessions_audit'] = dict(m1158_z=round(r.z, 1), m1158_rate=round(r.hp / r.sp, 4), m1158_spins=int(r.sp),
                             others_sd=round(o.z.std(), 3), others_max=round(o.z.abs().max(), 1))

# 5. Comps by player loss decile, and who absorbed the May 1 change
pp = c.sql(f"select player_id, period_month, tracked_net_usd net, theo_usd theo, comp_cost_usd comp from '{D}1_prepared_views/player_period.parquet'").df()
y = pp.groupby('player_id')[['net', 'theo', 'comp']].sum()
y['dec'] = pd.qcut(y.net.rank(method='first'), 10, labels=False)  # 0 = largest tracked losses
dg = y.groupby('dec')[['net', 'theo', 'comp']].sum()
pp = pp.merge(y[['dec']], left_on='player_id', right_index=True)
pp['post'] = pp.period_month >= '2025-05'
cg = pp.assign(top=pp.dec == 0).groupby(['top', 'post'])[['comp', 'theo']].sum()
cpt = (cg.comp / cg.theo)
out['comp_dist'] = dict(
    loss_share=(dg.net / dg.net.sum()).round(3).tolist(), comp_share=(dg.comp / dg.comp.sum()).round(3).tolist(),
    comp_per_theo=(dg.comp / dg.theo).round(4).tolist(),
    top_pre=round(cpt[(True, False)], 4), top_post=round(cpt[(True, True)], 4),
    rest_pre=round(cpt[(False, False)], 4), rest_post=round(cpt[(False, True)], 4))

# 6. Points liability: what the outstanding balance is worth at the old vs new point price
L = f"'{D}3_guests/loyalty_ledger.parquet'"
bal = c.sql(f"select sum(points_delta)::double from {L}").fetchall()[0][0]
rd = c.sql(f"""select event_at_utc >= timestamp '2025-05-01 13:00' post, -sum(points_delta)::double / (sum(face_value_cents)/100.0) ppd,
  sum(economic_cost_cents)::double / sum(face_value_cents) cf, count(*)::double / count(distinct cast(event_at_utc as date)) nday,
  sum(face_value_cents)/100.0 / count(distinct cast(event_at_utc as date)) fday
  from {L} where event_type='redeem' and event_at_utc >= timestamp '2025-04-01 13:00' group by 1 order by 1""").df()  # April price vs May-Jun price
pre, post = rd.iloc[0], rd.iloc[1]
out['liability'] = dict(points=bal, ppd_pre=round(pre.ppd, 2), ppd_post=round(post.ppd, 2), cost_face=round(post.cf, 3),
                        econ_pre=round(bal / pre.ppd * pre.cf, 0), econ_post=round(bal / post.ppd * post.cf, 0),
                        redeem_day_pre=round(pre.nday, 0), redeem_day_post=round(post.nday, 0),
                        face_day_pre=round(pre.fday, 0), face_day_post=round(post.fday, 0))

# 7. Security incidents (inspection leads, not accusations) and the B-38 swap
inc = c.sql(f"select category, count(*) n, count(distinct machine_id) m, max(cnt) mx from (select *, count(*) over (partition by category, machine_id) cnt from '{D}5_optional/security_incidents.parquet') group by 1 order by 2 desc").df()
out['incidents'] = dict(by_cat=inc.to_dict('records'),
                        m1158=int(c.sql(f"select count(*) from '{D}5_optional/security_incidents.parquet' where machine_id='M-1158'").fetchall()[0][0]))
sw = c.sql("""select machine_id, any_value(bank_id) bank, min(gaming_date) d0, max(gaming_date) d1, sum(theo_usd)/count(*) theo_day,
  sum(coin_in_usd)/count(*) ci_day from d where machine_id in ('M-1120','M-5076') group by 1 order by 3""").df()
out['swap'] = sw.astype({'d0': str, 'd1': str}).round(1).to_dict('records')

def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list): return [clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating, float)): return None if np.isnan(o) else float(o)
    return o
json.dump(clean(out), open('analysis/deep.json', 'w'))
for k, v in out.items():
    print(k, {kk: vv for kk, vv in v.items() if not isinstance(vv, list)} if isinstance(v, dict) else v)

# 8. Can relocation capture unmet demand? Free slots and occupancy by zone (after the walkway reopened)
cap = c.sql(f"""with s as (select location_id, zone_id from '{D}2_machine_decision/floor_locations.parquet' where node_type='slot'),
 u as (select distinct location_id from {PDV} where gaming_date='2025-06-30' and location_id is not null),
 o as (select zone_id, sum(occupied_hours)/sum(available_hours) occ, sum(theo_usd)/count(*) theo_day from d where gaming_date >= '2025-04-07' group by 1)
 select s.zone_id, count(*) slots, count(*) - count(u.location_id) free, any_value(o.occ) occ, any_value(o.theo_day) theo_day
 from s left join u using(location_id) join o using(zone_id) group by 1 order by occ desc""").df()
out['capacity'] = cap.round(3).to_dict('records')
json.dump(clean(out), open('analysis/deep.json', 'w'))
print('capacity', cap.round(3).to_dict('records'))

# 9. Seasonality: each month vs its own weekday mix (weekday means from Jan-May)
x = c.sql(f"select gaming_date gd, coin_in_usd ci from '{D}1_prepared_views/property_day.parquet'").df()
x['gd'] = pd.to_datetime(x.gd); x['wd'] = x.gd.dt.dayofweek; x['mo'] = x.gd.dt.strftime('%Y-%m')
x['exp'] = x.wd.map(x[x.mo <= '2025-05'].groupby('wd').ci.mean())
sg = x.groupby('mo')[['ci', 'exp']].mean()
out['season_gap'] = (sg.ci / sg.exp - 1).round(4).to_dict()
json.dump(clean(out), open('analysis/deep.json', 'w'))
print('season_gap', out['season_gap'])
