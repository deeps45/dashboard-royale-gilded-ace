import duckdb
con=duckdb.connect()
con.sql("""create view md as select m.*, g.payout_multiplier_variance v, g.configured_rtp rtp, g.volatility_class vol
from 'data/2_machine_decision/machine_day.parquet' m join 'data/2_machine_decision/game_math.parquet' g using(config_id)""")
con.sql("""create table mach as select machine_id,
 count(*) filter (where location_id is not null) days_on_floor,
 sum(coin_in_cents)/100 coin_in, sum(house_win_cents)/100 hw, sum(theo_cents)/100 theo,
 sum(house_win_cents)/nullif(sum(coin_in_cents),0) hold, 1-sum(payout_cents)/nullif(sum(coin_in_cents),0) chk,
 any_value(rtp) rtp, any_value(vol) vol, count(distinct config_id) ncfg,
 sum(available_seconds)/nullif(sum(scheduled_seconds) filter (where location_id is not null),0) avail,
 sum(occupied_seconds)/nullif(sum(available_seconds),0) occ,
 (sum(house_win_cents)-sum(theo_cents))/100 luck,
 sqrt(sum(sum_bet_squared*v))/100 sd
 from md group by 1""")
con.sql("alter table mach add column z double; update mach set z=luck/nullif(sd,0)")
print("== GM bottom 10 by house win ==")
con.sql("select machine_id,days_on_floor d,round(hw) hw,round(theo) theo,round(z,2) z,round(hold,4) hold,1-rtp exp_hold,vol,round(avail,3) avail,round(occ,3) occ,ncfg from mach order by hw limit 10").show(max_width=250)
print("== most extreme luck z (both tails) ==")
con.sql("select machine_id,round(hw) hw,round(theo) theo,round(z,2) z,round(hold,4) hold,1-rtp exp_hold,vol,ncfg from mach order by abs(z) desc limit 12").show(max_width=250)
print("== z distribution ==")
con.sql("select round(stddev(z),2) sd_z, round(avg(z),2) mean_z, count(*) filter(where abs(z)>3) n_gt3 from mach").show()
print("== lowest availability ==")
con.sql("select machine_id,round(avail,3) avail,round(hw) hw,round(theo) theo from mach order by avail limit 10").show()
con.sql("copy mach to 'analysis/mach.parquet'")
