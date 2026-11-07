import duckdb
con=duckdb.connect()
L="'data/3_guests/loyalty_ledger.parquet'"; F="'data/3_guests/fnb_transactions.parquet'"
con.sql(f"""select strftime(event_at_local,'%m') m, count(*) n, count(comp_id) n_comp, round(sum(face_value_cents) filter(where comp_id is not null)/100) comp_face, round(sum(cogs_cents) filter(where comp_id is not null)/100) comp_cogs, round(sum(cash_receipt_cents)/100) cash, round(sum(cogs_cents)/100) cogs, count(player_id) carded from {F} group by 1 order by 1""").show()
con.sql(f"""select strftime(event_at_utc,'%m') m, benefit_id, count(*) n, sum(points_delta) pts, round(sum(face_value_cents)/100) face, round(sum(economic_cost_cents)/100) cost from {L} where event_type='redeem' group by all order by benefit_id, m""").show(max_rows=60)
con.sql(f"""select strftime(event_at_utc,'%m') m, tier_after, count(*) from {L} where tier_before<>tier_after group by all order by all""").show(max_rows=40)
