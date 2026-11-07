import duckdb
con=duckdb.connect()
P="'data/1_prepared_views/prepared_daily_view.parquet'"
con.sql("select * from 'data/2_machine_decision/floor_walkways.parquet'").show(max_width=200)
con.sql("select event_id,name,event_type,start_date,end_date,local_scope from 'data/4_context/events.parquet'").show(max_width=200)
print("== M-1158 hold pre/post 2025-03-10 and post-June-?")
con.sql(f"""select case when gaming_date<'2025-03-10' then 'a_pre' when gaming_date<'2025-06-01' then 'b_mar10-may' else 'c_jun' end p, round(sum(house_win_usd)/sum(coin_in_usd),4) hold, round(sum(luck_residual_usd)) luck from {P} where machine_id='M-1158' group by 1 order by 1""").show()
print("== zone x month theo per machine-day ==")
con.sql(f"""pivot (select zone_name, month, sum(theo_usd)/count(*) t from {P} where location_id is not null group by all) on month using round(first(t)) order by zone_name""").show(max_width=250)
print("== property monthly ==")
con.sql("""select strftime(gaming_date,'%Y-%m') m, round(sum(coin_in_usd)/1e6,2) ci_m, round(sum(house_win_usd)/sum(coin_in_usd),4) hold, round(sum(theo_usd)/sum(coin_in_usd),4) thold,
 round(sum(available_machine_hours)/sum(active_machines*24),4) av, round(sum(occupied_machine_hours)/sum(available_machine_hours),3) occ, sum(faults_opened) faults,
 round(sum(comp_cost_usd)) comp_cost, round(sum(comp_face_value_usd)) comp_face, round(sum(comp_cost_usd)/sum(theo_usd),4) comp_pct_theo, round(sum(pos_cash_usd)) fnb_cash, round(sum(total_zone_entries_observed)/1e3) entries_k, round(avg(counter_coverage_share),3) cov
 from 'data/1_prepared_views/property_day.parquet' group by 1 order by 1""").show(max_width=250)
