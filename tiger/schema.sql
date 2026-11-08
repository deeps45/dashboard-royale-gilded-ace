-- Gilded Ace on Tiger Data (TimescaleDB). Idempotent: drops and rebuilds everything.
DROP MATERIALIZED VIEW IF EXISTS leak_hourly CASCADE;
DROP MATERIALIZED VIEW IF EXISTS meter_daily CASCADE;
DROP MATERIALIZED VIEW IF EXISTS traffic_daily CASCADE;
DROP TABLE IF EXISTS meter_hour, zone_traffic, machine_dim, game_math, location_dim CASCADE;

-- Relational dimensions live next to the time series (one database, one SQL dialect)
CREATE TABLE game_math (config_id text PRIMARY KEY, theme text, configured_rtp double precision,
  hit_probability double precision, payout_multiplier_variance double precision, volatility_class text);
CREATE TABLE machine_dim (machine_id text PRIMARY KEY, config_id text REFERENCES game_math, manufacturer text, theme text);
CREATE TABLE location_dim (location_id text PRIMARY KEY, zone_id text, bank_id text, x_m double precision, y_m double precision);

-- Hourly meters for every machine: the high-frequency stream
CREATE TABLE meter_hour (
  ts timestamptz NOT NULL, machine_id text NOT NULL, location_id text, gaming_date date,
  available_s int, occupied_s int, spins bigint, hits bigint,
  coin_in_cents bigint, payout_cents bigint, carded_coin_in_cents bigint
) WITH (tsdb.hypertable, tsdb.partition_column = 'ts', tsdb.chunk_interval = '7 days',
        tsdb.segmentby = 'machine_id', tsdb.orderby = 'ts DESC');

-- Door/zone counters (offline hours stay NULL, never zero)
CREATE TABLE zone_traffic (
  ts timestamptz NOT NULL, sensor_id text NOT NULL, zone_id text, entries int, counter_status text, coverage_minutes int
) WITH (tsdb.hypertable, tsdb.partition_column = 'ts', tsdb.chunk_interval = '30 days',
        tsdb.segmentby = 'sensor_id', tsdb.orderby = 'ts DESC');
