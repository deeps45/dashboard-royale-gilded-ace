"""Export compact JSON for the dashboard (docs/data.json). All money in USD."""
import duckdb, json, pandas as pd
con=duckdb.connect()
q=lambda s: con.sql(s).df()
md=q("""select m.machine_id, m.gaming_date::varchar d, l.bank_id, l.zone_id, coin_in_cents/100.0 ci, house_win_cents/100.0 hw, theo_cents/100.0 th,
 sum_bet_squared*g.payout_multiplier_variance/1e4 var, available_seconds/3600.0 av, scheduled_seconds/3600.0 sc, occupied_seconds/3600.0 oc, paid_spins sp, payout_positive_spins hi
 from 'data/2_machine_decision/machine_day.parquet' m join 'data/2_machine_decision/game_math.parquet' g using(config_id)
 left join 'data/2_machine_decision/floor_locations.parquet' l on l.location_id=m.location_id where m.location_id is not null order by d, machine_id""")
dates=sorted(md.d.unique()); D={x:i for i,x in enumerate(dates)}
mids=sorted(md.machine_id.unique()); M={x:i for i,x in enumerate(mids)}
banks=sorted(md.bank_id.dropna().unique()); B={x:i for i,x in enumerate(banks)}
zones=q("select distinct zone_id, zone_name from 'data/1_prepared_views/prepared_daily_view.parquet' where zone_id is not null").set_index('zone_id').zone_name.to_dict()
bz=md.groupby('bank_id').zone_id.first().to_dict()
meta=q("""select m.machine_id, manufacturer, m.theme, g.configured_rtp::double rtp, g.volatility_class vol, g.hit_probability::double hp, install_date::varchar inst, retire_date::varchar ret
 from 'data/2_machine_decision/machines.parquet' m join (select machine_id, any_value(config_id) c from 'data/2_machine_decision/machine_day.parquet' group by 1) x using(machine_id) join 'data/2_machine_decision/game_math.parquet' g on g.config_id=x.c""").set_index('machine_id')
cols={'m':md.machine_id.map(M),'d':md.d.map(D),'b':md.bank_id.map(B),'ci':md.ci.round(0),'hw':md.hw.round(0),'th':md.th.round(0),'v':md['var'].round(0),'av':md.av.round(2),'sc':md.sc.round(2),'oc':md.oc.round(2),'sp':md.sp,'hi':md.hi}
out={'dates':dates,'machines':[[x,*meta.loc[x,['manufacturer','theme','rtp','vol','hp']].tolist()] for x in mids],
 'banks':[[b,bz[b]] for b in banks],'zones':zones,'md':{k:v.astype(int if k in('m','d','b','sp','hi') else float).tolist() for k,v in cols.items()}}
out['md']={k:[int(x) if k in('m','d','b','ci','hw','th','v','sp','hi') else x for x in v] for k,v in out['md'].items()}
pdx=q("""select gaming_date::varchar d, local_weekday wd, coin_in_usd::double ci, house_win_usd::double hw, theo_usd::double th, comp_cost_usd::double cc, comp_face_value_usd::double cf,
 pos_cash_usd::double fnb, faults_opened f, total_zone_entries_observed::double ent, counter_coverage_share::double cov, available_machine_hours::double avh, occupied_machine_hours::double och, active_machines am, events_active ev,
 contribution_after_supplied_costs_usd::double contrib from 'data/1_prepared_views/property_day.parquet' order by 1""")
out['prop']=pdx.round(2).to_dict('list')
out['model']=json.load(open('analysis/model_summary.json')); out['preds']=json.load(open('analysis/model_preds.json'))
pp=q("""select period_month mo, opening_tier tier, age_band age, home_region reg, count(*) n, sum(tracked_coin_in_usd)::double ci, sum(tracked_payout_usd)::double po, sum(theo_usd)::double th,
 sum(comp_cost_usd)::double cc, sum(comp_face_value_usd)::double cf, sum(points_earned)::double pe, sum(points_redeemed)::double pr, sum(tracked_contribution_usd)::double contrib,
 count(*) filter (where tracked_net_usd>0) nwin from 'data/1_prepared_views/player_period.parquet' group by all""")
out['pp']=pp.round(0).to_dict('list')
# concentration: per-player 6-month net loss, Lorenz by tier group
pl=q("""select opening_tier tier, -sum(tracked_net_usd)::double loss, sum(theo_usd)::double th from 'data/1_prepared_views/player_period.parquet' group by player_id, opening_tier""")
def lor(s):
    s=s.sort_values(ascending=False).reset_index(drop=True); c=s.cumsum()/s.sum(); n=len(s)
    return [[round(p,3), round(float(c.iloc[max(0,int(p*n)-1)]),4)] for p in [.001,.005,.01,.02,.05,.1,.2,.3,.5,.75,1]]
out['lorenz']={'All':lor(pl.th),**{t:lor(g.th) for t,g in pl.groupby('tier')}}
out['winners']={'players':len(pl),'net_winners':int((pl.loss<0).sum()),'top1_loss_share':round(float(pl.loss.sort_values(ascending=False).head(len(pl)//100).sum()/pl.loss.sum()),3)}
out['comp_rate']=q("""select cast(event_at_utc - interval 13 hour as date)::varchar d, -sum(points_delta)/sum(face_value_cents)*100 ppd, count(*) n, sum(economic_cost_cents)/100.0 cost
 from 'data/3_guests/loyalty_ledger.parquet' where event_type='redeem' and event_at_utc<'2025-07-01 13:00' group by 1 order by 1""").round(2).to_dict('list')
ops=q("""select o.machine_id, m.manufacturer mf, strftime(opened_at_local,'%Y-%m') mo,
 case when hour(opened_at_local)>=6 and hour(opened_at_local)<14 then 'Day' when hour(opened_at_local)>=14 and hour(opened_at_local)<22 then 'Swing' else 'Grave' end sh,
 epoch(work_started_at_utc-opened_at_utc)/3600 wait, epoch(available_at_utc-opened_at_utc)/3600 down, direct_cost_cents/100.0 cost
 from 'data/2_machine_decision/operations.parquet' o join 'data/2_machine_decision/machines.parquet' m using(machine_id) where event_type='fault_repair'""")
out['ops']=ops.groupby(['mf','mo','sh']).agg(n=('cost','size'),wait=('wait','sum'),down=('down','sum'),cost=('cost','sum')).round(2).reset_index().to_dict('list')
out['mf_count']=meta.manufacturer.value_counts().to_dict()
out['model2']=json.load(open('analysis/model2.json'))
out['staff']=q("""with o as (select cast(opened_at_utc - interval 13 hour as date) gd, case when hour(opened_at_local)>=6 and hour(opened_at_local)<14 then 'day' when hour(opened_at_local)>=14 and hour(opened_at_local)<22 then 'swing' else 'grave' end shift,
 epoch(work_started_at_utc-opened_at_utc)/3600 w from 'data/2_machine_decision/operations.parquet' where event_type='fault_repair'),
r as (select gaming_date, shift, actual_headcount techs from 'data/5_optional/shift_roster.parquet' where role='slot_tech')
select o.shift, r.techs, count(*) n, avg(w) wait from o join r on r.gaming_date=o.gd and r.shift=o.shift group by all order by all""").round(2).to_dict('records')
out['roster']=q("""select strftime(gaming_date,'%Y-%m') mo, shift, avg(planned_headcount) plan, avg(actual_headcount) act from 'data/5_optional/shift_roster.parquet' where role='slot_tech' group by all order by all""").round(2).to_dict('list')
out['events']=q("select name, event_type, start_date::varchar s, end_date::varchar e, announced_date::varchar a from 'data/4_context/events.parquet'").to_dict('records')
out['actions']=q("select action_type_id id, name, unit_cost_cents/100.0 cost, recurring_cost_cents_per_day/100.0 rec, lead_days lead, quantity_limit lim, incompatibility_group grp from 'data/2_machine_decision/action_catalog.parquet'").to_dict('records')
s=json.dumps(out,separators=(',',':'),default=str).replace('NaN','null'); open('docs/data.json','w').write(s); print(len(s)/1e6,'MB', len(dates), len(mids), len(banks))
