"""Gilded Ace on Tiger Data: load -> verify -> benchmark (row store vs columnstore vs continuous aggregates) -> leak early-warning.
Usage: .venv/bin/python tiger/run.py   (needs TIGER_URL in .env; writes analysis/tiger.json)"""
import os, io, json, time, statistics, duckdb, psycopg
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB = os.environ['TIGER_URL']; D = 'data/'
dk = duckdb.connect(); out = {}
conn = psycopg.connect(DB, autocommit=True); cur = conn.cursor()
sql = lambda q, a=None: cur.execute(q, a)
one = lambda q, a=None: cur.execute(q, a).fetchone()[0]

def copy(table, cols, query, chunk=250_000):
    rel = dk.sql(query); n = 0; t0 = time.time()
    with cur.copy(f"COPY {table} ({','.join(cols)}) FROM STDIN WITH (FORMAT csv, NULL '')") as cp:
        for batch in rel.to_arrow_reader(chunk):
            df = batch.to_pandas()
            if df.empty: continue
            buf = io.StringIO(); df.to_csv(buf, header=False, index=False); cp.write(buf.getvalue()); n += len(df)
    print(f'  {table}: {n:,} rows in {time.time() - t0:.1f}s'); return n

print('1. schema'); sql(open(os.path.join(os.path.dirname(__file__), 'schema.sql')).read())
print('2. load')
copy('game_math', ['config_id', 'theme', 'configured_rtp', 'hit_probability', 'payout_multiplier_variance', 'volatility_class'],
     f"select config_id, theme, configured_rtp, hit_probability, payout_multiplier_variance, volatility_class from '{D}2_machine_decision/game_math.parquet'")
copy('machine_dim', ['machine_id', 'config_id', 'manufacturer', 'theme'],
     f"""select m.machine_id, c.config_id, m.manufacturer, m.theme from '{D}2_machine_decision/machines.parquet' m
         join (select machine_id, any_value(config_id) config_id from '{D}2_machine_decision/machine_day.parquet' where config_id is not null group by 1) c using(machine_id)""")
copy('location_dim', ['location_id', 'zone_id', 'bank_id', 'x_m', 'y_m'],
     f"select location_id, zone_id, bank_id, x_m, y_m from '{D}2_machine_decision/floor_locations.parquet' where node_type='slot'")
rows = copy('meter_hour', ['ts', 'machine_id', 'location_id', 'gaming_date', 'available_s', 'occupied_s', 'spins', 'hits', 'coin_in_cents', 'payout_cents', 'carded_coin_in_cents'],
     f"""select strftime(hour_start_utc, '%Y-%m-%d %H:%M:%S+00'), machine_id, location_id, gaming_date::date, available_seconds, occupied_seconds,
         paid_spins, payout_positive_spins, coin_in_cents, payout_cents, carded_coin_in_cents from '{D}5_optional/machine_hour.parquet' where location_id is not null""")
copy('zone_traffic', ['ts', 'sensor_id', 'zone_id', 'entries', 'counter_status', 'coverage_minutes'],
     f"select strftime(hour_start_utc, '%Y-%m-%d %H:%M:%S+00'), sensor_id, zone_id, entries_count::varchar, counter_status, coverage_minutes::varchar from '{D}4_context/zone_traffic_hourly.parquet'")
sql('ANALYZE')

print('3. parity with the local analysis')
loc = dk.sql(f"select sum(coin_in_cents)::bigint, sum(paid_spins)::bigint, sum(payout_positive_spins)::bigint from '{D}5_optional/machine_hour.parquet' where location_id is not null").fetchall()[0]
tig = cur.execute('select sum(coin_in_cents)::bigint, sum(spins)::bigint, sum(hits)::bigint from meter_hour').fetchone()
out['parity'] = {'rows': rows, 'local': list(map(int, loc)), 'tiger': list(map(int, tig)), 'match': tuple(map(int, loc)) == tuple(map(int, tig))}
print('  ', out['parity'])

Q = {  # the two questions the dashboard asks most often
 'leak_monitor': """select h.machine_id, sum(h.hits) hits, sum(h.spins) spins,
     (sum(h.hits) - g.hit_probability * sum(h.spins)) / sqrt(g.hit_probability * (1 - g.hit_probability) * sum(h.spins)) z
   from meter_hour h join machine_dim m using(machine_id) join game_math g using(config_id)
   group by h.machine_id, g.hit_probability having sum(h.spins) > 0 order by abs((sum(h.hits) - g.hit_probability * sum(h.spins)) / sqrt(g.hit_probability * (1 - g.hit_probability) * sum(h.spins))) desc limit 10""",
 'zone_day': """select l.zone_id, (time_bucket('1 day', h.ts, 'America/Los_Angeles', "offset" => interval '6 hours') at time zone 'America/Los_Angeles')::date gd,
     sum(h.coin_in_cents) / 100.0 coin_in from meter_hour h join location_dim l using(location_id) group by 1, 2""",
}
QC = {  # same answers from the continuous aggregate
 'leak_monitor': """select d.machine_id, sum(d.hits) hits, sum(d.spins) spins,
     (sum(d.hits) - g.hit_probability * sum(d.spins)) / sqrt(g.hit_probability * (1 - g.hit_probability) * sum(d.spins)) z
   from meter_daily d join machine_dim m using(machine_id) join game_math g using(config_id)
   group by d.machine_id, g.hit_probability having sum(d.spins) > 0 order by abs((sum(d.hits) - g.hit_probability * sum(d.spins)) / sqrt(g.hit_probability * (1 - g.hit_probability) * sum(d.spins))) desc limit 10""",
 'zone_day': """select l.zone_id, (d.day at time zone 'America/Los_Angeles')::date gd, sum(d.coin_in_cents) / 100.0 coin_in
   from meter_daily d join location_dim l using(location_id) group by 1, 2""",
}
def bench(q, n=5):  # server-side execution time from EXPLAIN ANALYZE: no network noise
    ts = []
    for _ in range(n):
        plan = cur.execute('EXPLAIN (ANALYZE, FORMAT JSON) ' + q).fetchone()[0][0]; ts.append(plan['Execution Time'])
    return round(statistics.median(ts), 1)

print('4. row store (uncompressed)')
size_row = one("select hypertable_size('meter_hour')")
out['bench'] = {'row': {k: bench(v) for k, v in Q.items()}}; print('  ', out['bench']['row'], f'{size_row / 1e6:.1f} MB')

print('5. columnstore (compression)')
t0 = time.time()
sql("select count(compress_chunk(c, if_not_compressed => true)) from show_chunks('meter_hour') c")
sql("select count(compress_chunk(c, if_not_compressed => true)) from show_chunks('zone_traffic') c")
size_col = one("select hypertable_size('meter_hour')"); sql('ANALYZE meter_hour')
out['bench']['columnstore'] = {k: bench(v) for k, v in Q.items()}
out['storage'] = {'row_mb': round(size_row / 1e6, 1), 'columnstore_mb': round(size_col / 1e6, 1), 'saving': round(1 - size_col / size_row, 3), 'compress_s': round(time.time() - t0, 1)}
print('  ', out['bench']['columnstore'], out['storage'])

print('6. continuous aggregates (gaming day = 06:00 Las Vegas time), real-time enabled')
sql("""CREATE MATERIALIZED VIEW meter_daily WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
 select time_bucket('1 day', ts, 'America/Los_Angeles', "offset" => interval '6 hours') as day, machine_id, location_id,
   sum(spins) spins, sum(hits) hits, sum(coin_in_cents) coin_in_cents, sum(payout_cents) payout_cents,
   sum(available_s) available_s, sum(occupied_s) occupied_s
 from meter_hour group by 1, 2, 3 WITH DATA""")
sql("""CREATE MATERIALIZED VIEW traffic_daily WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
 select time_bucket('1 day', ts, 'America/Los_Angeles', "offset" => interval '6 hours') as day, zone_id,
   sum(entries) entries, sum(coverage_minutes) coverage_minutes, count(*) filter (where counter_status = 'offline') offline_hours
 from zone_traffic group by 1, 2 WITH DATA""")
sql("select add_continuous_aggregate_policy('meter_daily', start_offset => interval '3 days', end_offset => interval '1 hour', schedule_interval => interval '15 minutes')")
sql("select add_continuous_aggregate_policy('traffic_daily', start_offset => interval '3 days', end_offset => interval '1 hour', schedule_interval => interval '15 minutes')")
sql('ANALYZE meter_daily')
out['bench']['cagg'] = {k: bench(v) for k, v in QC.items()}
out['cagg_rows'] = one('select count(*) from meter_daily')
same = [r[0] for r in cur.execute(Q['leak_monitor']).fetchall()] == [r[0] for r in cur.execute(QC['leak_monitor']).fetchall()]
out['cagg_same_answer'] = same
print('  ', out['bench']['cagg'], 'rows', out['cagg_rows'], 'same answer as raw:', same)

# live monitor view the floor team can query any time
sql("""CREATE OR REPLACE VIEW leak_monitor AS
 select d.machine_id, m.theme, g.config_id, sum(d.spins) spins, sum(d.hits)::double precision / nullif(sum(d.spins), 0) hit_rate, g.hit_probability configured,
   (sum(d.hits) - g.hit_probability * sum(d.spins)) / sqrt(g.hit_probability * (1 - g.hit_probability) * nullif(sum(d.spins), 0)) hit_z
 from meter_daily d join machine_dim m using(machine_id) join game_math g using(config_id)
 group by d.machine_id, m.theme, g.config_id, g.hit_probability""")
out['leak_monitor_top'] = [list(r) for r in cur.execute("select machine_id, theme, round(hit_rate::numeric, 4)::float, configured, round(hit_z::numeric, 1)::float from leak_monitor order by abs(hit_z) desc limit 5").fetchall()]

print('7. early warning: when would a live hourly monitor have caught M-1158?')
ew = cur.execute("""
 with c as (
   select h.machine_id, h.ts, g.hit_probability p,
     sum(h.hits) over w ch, sum(h.spins) over w cs, sum(h.coin_in_cents) over w cci
   from meter_hour h join machine_dim m using(machine_id) join game_math g using(config_id)
   window w as (partition by h.machine_id order by h.ts rows unbounded preceding))
 , z as (select machine_id, ts, cs, cci, (ch - p * cs) / sqrt(p * (1 - p) * cs) z from c where cs > 0)
 select machine_id, min(ts) filter (where abs(z) >= 5) first_alarm, max(abs(z)) max_abs_z,
   min(cs) filter (where abs(z) >= 5) spins_at_alarm, (array_agg(cci order by ts) filter (where abs(z) >= 5))[1] coin_in_at_alarm,
   min(ts) first_play
 from z group by machine_id order by first_alarm nulls last, max_abs_z desc""").fetchall()
alarms = [r for r in ew if r[1] is not None]
others = [r for r in ew if r[0] != 'M-1158']
m = next(r for r in ew if r[0] == 'M-1158')
hours = (m[1] - m[5]).total_seconds() / 3600
out['early_warning'] = {'threshold': 5, 'machines_alarmed': [r[0] for r in alarms], 'm1158_first_alarm': m[1].isoformat(), 'm1158_first_play': m[5].isoformat(),
                        'm1158_hours_to_alarm': round(hours, 1), 'm1158_spins_at_alarm': int(m[3]), 'm1158_coin_in_at_alarm': round(m[4] / 100, 0),
                        'false_alarms': len([r for r in alarms if r[0] != 'M-1158']), 'max_abs_z_others': round(max(r[2] for r in others), 2)}
print('  ', out['early_warning'])
out['versions'] = {'postgres': one('show server_version'), 'timescaledb': one("select extversion from pg_extension where extname='timescaledb'")}
json.dump(out, open('analysis/tiger.json', 'w'), indent=1, default=str)
print('wrote analysis/tiger.json')
