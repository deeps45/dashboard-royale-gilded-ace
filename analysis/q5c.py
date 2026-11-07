import duckdb
con=duckdb.connect()
con.sql("""select cast(event_at_utc - interval 13 hour as date) d, round(-sum(points_delta)/sum(face_value_cents)*100,1) pts_per_usd, count(*) n from 'data/3_guests/loyalty_ledger.parquet' where event_type='redeem' and event_at_utc between '2025-04-25' and '2025-05-06' group by 1 order by 1""").show()
# downtime cost: lost theo = unavailable hours * machine's theo per occupied-available hour * occupancy
con.sql("""select month, round(sum(24*0+ (available_hours/nullif(availability_ratio,0) - available_hours))) down_h,
 round(sum((available_hours/nullif(availability_ratio,0) - available_hours) * theo_usd/nullif(available_hours,0))) lost_theo
 from 'data/1_prepared_views/prepared_daily_view.parquet' where location_id is not null and available_hours>0 group by 1 order by 1""").show()
con.sql("""select m.manufacturer, round(sum((available_hours/nullif(availability_ratio,0) - available_hours) * theo_usd/nullif(available_hours,0))) lost_theo, round(sum(repair_cost_usd)) repair_cost
 from 'data/1_prepared_views/prepared_daily_view.parquet' m where location_id is not null and available_hours>0 group by 1""").show()
