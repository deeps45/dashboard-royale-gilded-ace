import duckdb
con=duckdb.connect()
O="'data/2_machine_decision/operations.parquet'"
print("== ops by type ==")
con.sql(f"""select event_type, count(*) n, round(median(epoch(work_started_at_utc-opened_at_utc))/3600,2) wait_h_med, round(avg(epoch(available_at_utc-opened_at_utc))/3600,2) down_h_avg, round(sum(epoch(available_at_utc-opened_at_utc))/3600) down_h_tot, round(sum(direct_cost_cents)/100) cost from {O} group by 1""").show()
print("== fault repairs: wait by local hour bucket & manufacturer ==")
con.sql(f"""select case when hour(opened_at_local) between 6 and 13 then 'day 6-14' when hour(opened_at_local) between 14 and 21 then 'swing 14-22' else 'grave 22-6' end sh, count(*) n, round(avg(epoch(work_started_at_utc-opened_at_utc))/3600,2) wait_h, round(avg(epoch(available_at_utc-work_started_at_utc))/3600,2) fix_h from {O} where event_type='fault_repair' group by 1""").show()
con.sql(f"""select m.manufacturer, count(distinct m.machine_id) nm, count(o.operation_id) faults, round(count(o.operation_id)/count(distinct m.machine_id),2) per_m, round(avg(epoch(available_at_utc-opened_at_utc))/3600,2) down_h from 'data/2_machine_decision/machines.parquet' m left join {O} o on o.machine_id=m.machine_id and o.event_type='fault_repair' group by 1 order by per_m desc""").show()
print("== roster: techs ==")
con.sql("select shift, role, round(avg(planned_headcount),2) plan, round(avg(actual_headcount),2) act, count(*) n from 'data/5_optional/shift_roster.parquet' group by all order by role, shift").show()
print("== players: concentration ==")
con.sql("""with p as (select player_id, sum(tracked_coin_in_usd) ci, sum(tracked_net_usd) net, sum(theo_usd) th from 'data/1_prepared_views/player_period.parquet' group by 1),
r as (select *, row_number() over (order by th desc) rk, count(*) over () N from p)
select round(sum(ci)/1e6,1) ci_m, round(sum(net)/1e6,2) net_m, round(sum(th)/1e6,2) theo_m, count(*) filter (where net>0) n_house_won, count(*) filter(where net<0) n_player_won,
round(sum(th) filter (where rk<=N*0.01)/sum(th),3) top1pct_theo, round(sum(th) filter (where rk<=N*0.1)/sum(th),3) top10pct_theo, round(sum(net) filter (where rk<=N*0.01)/sum(net),3) top1pct_net from r""").show()
print("== tracked_net sign convention check ==")
con.sql("select round(sum(tracked_coin_in_usd)) ci, round(sum(tracked_payout_usd)) po, round(sum(tracked_net_usd)) net from 'data/1_prepared_views/player_period.parquet'").show()
print("== loyalty by month/type ==")
con.sql("""pivot (select strftime(event_at_utc,'%m') m, event_type, sum(points_delta) pts from 'data/3_guests/loyalty_ledger.parquet' group by all) on m using sum(pts)""").show(max_width=250)
print("== comps by tier & month: comp cost / theo ==")
con.sql("""pivot (select opening_tier, period_month, sum(comp_cost_usd)/nullif(sum(theo_usd),0) r from 'data/1_prepared_views/player_period.parquet' group by all) on period_month using round(first(r),4)""").show(max_width=250)
con.sql("""pivot (select opening_tier, period_month, sum(points_earned)/nullif(sum(tracked_coin_in_usd),0)*100 r from 'data/1_prepared_views/player_period.parquet' group by all) on period_month using round(first(r),3)""").show(max_width=250)
