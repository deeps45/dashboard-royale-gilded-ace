"""Hit-frequency audit: does each machine pay on the share of spins its configured game says it should?
z_hit = (hits - p*spins)/sqrt(p(1-p)*spins). Independent of payout size, so nearly luck-free at high spin counts."""
import duckdb
r=duckdb.sql("""select machine_id, config_id, sum(paid_spins) spins, sum(payout_positive_spins) hits, any_value(g.hit_probability)::double p,
 (sum(payout_positive_spins)-any_value(g.hit_probability)::double*sum(paid_spins))/sqrt(any_value(g.hit_probability)::double*(1-any_value(g.hit_probability)::double)*sum(paid_spins)) z_hit
 from 'data/2_machine_decision/machine_day.parquet' m join 'data/2_machine_decision/game_math.parquet' g using(config_id) where paid_spins>0 group by 1,2""")
print(duckdb.sql("select round(stddev(z_hit),2) sd, count(*) filter(where abs(z_hit)>4) n_gt4 from r"))
print(duckdb.sql("select machine_id, config_id, spins, round(hits/spins,4) rate, p, round(z_hit,1) z from r order by abs(z_hit) desc limit 6"))
# by month for flagged
print(duckdb.sql("""select machine_id, strftime(gaming_date,'%m') mo, round(sum(payout_positive_spins)/sum(paid_spins),4) rate from 'data/2_machine_decision/machine_day.parquet'
 where machine_id in (select machine_id from r where abs(z_hit)>5) group by all order by all"""))
duckdb.sql("copy (select machine_id, z_hit, hits/spins rate, p from r) to 'analysis/hit_audit.csv'")
