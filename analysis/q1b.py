import duckdb
con=duckdb.connect()
P="'data/1_prepared_views/prepared_daily_view.parquet'"
print("== M-1158 monthly ==")
con.sql(f"""select month, any_value(zone_name) z, any_value(bank_id) b, round(sum(coin_in_usd)) ci, round(sum(house_win_usd)/sum(coin_in_usd),4) hold, any_value(theo_hold) th, round(avg(availability_ratio),3) av, sum(faults_opened) f
from {P} where machine_id='M-1158' group by 1 order by 1""").show()
print("== M-1158 ops ==")
con.sql("select event_type, opened_at_local, direct_cost_cents from 'data/2_machine_decision/operations.parquet' where machine_id='M-1158'").show()
print("== hold deviation by month: machines with monthly z<-3 ==")
con.sql("""create view md as select m.*, g.payout_multiplier_variance v from 'data/2_machine_decision/machine_day.parquet' m join 'data/2_machine_decision/game_math.parquet' g using(config_id)""")
con.sql("""select machine_id, month(gaming_date) mo, round((sum(house_win_cents)-sum(theo_cents))/sqrt(sum(sum_bet_squared*v)),2) z, round(sum(house_win_cents)/sum(coin_in_cents),4) hold
from md where coin_in_cents>0 group by 1,2 having abs(z)>3 order by z""").show()
print("== zones: theo per machine-day, availability, occupancy ==")
con.sql(f"""select zone_name, count(distinct machine_id) n, round(sum(theo_usd)/count(*)) theo_per_day, round(sum(occupied_hours)/sum(available_hours),3) occ, round(sum(available_hours)/sum(available_hours+0)/1,3) x,
 round(avg(availability_ratio),4) av, sum(faults_opened) faults
from {P} where location_id is not null group by 1 order by theo_per_day""").show()
print("== bottom10 zones/banks & theo per day ==")
con.sql(f"""select machine_id, any_value(zone_name) z, any_value(bank_id) b, count(distinct location_id) nloc, round(sum(theo_usd)/count(*)) theo_day, min(gaming_date) first, max(gaming_date) last
from {P} where location_id is not null and machine_id in ('M-5076','M-1158','M-1120','M-1118','M-1238','M-1181','M-1035','M-1179','M-1017','M-1265') group by 1 order by theo_day""").show()
