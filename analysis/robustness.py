"""Robustness checks for the headline findings. Writes analysis/robustness.json."""
import duckdb, numpy as np, pandas as pd, json
con=duckdb.connect(); R={}
md=con.sql("""select m.machine_id, m.gaming_date::date d, l.zone_id z, theo_cents/100.0 th, house_win_cents/100.0 hw, sum_bet_squared*g.payout_multiplier_variance/1e4 v,
 paid_spins sp, payout_positive_spins hi, g.hit_probability::double p from 'data/2_machine_decision/machine_day.parquet' m join 'data/2_machine_decision/game_math.parquet' g using(config_id)
 join 'data/2_machine_decision/floor_locations.parquet' l on l.location_id=m.location_id""").df(); md['d']=pd.to_datetime(md.d)
# 1. Placebo DiD: 35-day fake closures for Back Forty across all other windows
day=md.groupby(['d',md.z=='Z-B40']).th.mean().unstack(); day.columns=['rest','bf']
def did(a,b):
    m=(day.index>=a)&(day.index<=b); return (day.bf[m].mean()/day.bf[~m].mean()-1)-(day.rest[m].mean()/day.rest[~m].mean()-1)
real=did('2025-03-04','2025-04-06'); real_m=(day.index>='2025-03-04')&(day.index<='2025-04-06')
plac=[did(s,s+pd.Timedelta(days=33)) for s in pd.date_range('2025-01-01','2025-05-27') if not ((s<=pd.Timestamp('2025-04-06'))&(s+pd.Timedelta(days=33)>=pd.Timestamp('2025-03-04')))]
R['did']={'real':real,'placebo_n':len(plac),'placebo_min':min(plac),'placebo_max':max(plac),'p_value':float(np.mean([x<=real for x in plac]))}
# 2. Luck z: stability across halves; calibration
def mz(df): g=df.groupby('machine_id'); return (g.hw.sum()-g.th.sum())/np.sqrt(g.v.sum())
z1,z2=mz(md[md.d<'2025-04-01']),mz(md[md.d>='2025-04-01']); zz=pd.concat([z1,z2],axis=1).dropna()
R['luck']={'sd_all':float(mz(md).std()),'corr_halves':float(zz.corr().iloc[0,1]),'corr_halves_excl_1158':float(zz.drop('M-1158',errors='ignore').corr().iloc[0,1]),'m1158_q1':float(z1['M-1158']),'m1158_q2':float(z2['M-1158'])}
# 3. Hit audit: calibration without M-1158, and M-1158 in each month
g=md.groupby('machine_id'); hz=(g.hi.sum()-g.p.first()*g.sp.sum())/np.sqrt(g.p.first()*(1-g.p.first())*g.sp.sum())
mo=md[md.machine_id=='M-1158'].groupby(md.d.dt.month); hzm=((mo.hi.sum()-mo.p.first()*mo.sp.sum())/np.sqrt(mo.p.first()*(1-mo.p.first())*mo.sp.sum()))
R['hit']={'sd_excl_1158':float(hz.drop('M-1158').std()),'max_abs_excl_1158':float(hz.drop('M-1158').abs().max()),'m1158':float(hz['M-1158']),'m1158_min_month_z':float(hzm.min())}
# 4. Bottom-10 verdict robust to period: Back Forty count and min coin-in ratio per window
pdv=con.sql("select machine_id, gaming_date::date d, zone_name, coin_in_usd::double ci, house_win_usd::double hw from 'data/1_prepared_views/prepared_daily_view.parquet' where location_id is not null").df(); pdv['d']=pd.to_datetime(pdv.d)
win={}
for name,a,b in [('H1','2025-01-01','2025-06-30'),('Q1','2025-01-01','2025-03-31'),('Q2','2025-04-01','2025-06-30')]:
    x=pdv[(pdv.d>=a)&(pdv.d<=b)]; m=x.groupby('machine_id').agg(hw=('hw','sum'),ci=('ci','sum'),n=('ci','size'),z=('zone_name','last')); m['cipd']=m.ci/m.n
    zmed=m.groupby('z').cipd.median(); m['rel']=m.cipd/m.z.map(zmed); b10=m.nsmallest(10,'hw')
    win[name]={'back_forty':int((b10.z=='Back Forty').sum()),'weak_play':int((b10.rel<0.75).sum()),'min_rel':float(b10.rel.min())}
R['bottom10']=win
# 5. Comp step: is May 1 the single biggest break? (largest day-over-day change in points/$)
c=con.sql("select cast(event_at_utc - interval 13 hour as date) d, -sum(points_delta)/sum(face_value_cents)*100 r from 'data/3_guests/loyalty_ledger.parquet' where event_type='redeem' and event_at_utc<'2025-07-01' group by 1 order by 1").df()
c['chg']=c.r.diff(); top=c.loc[c.chg.abs().idxmax()]
R['comp']={'break_date':str(top.d)[:10],'break_size':float(top.chg),'second_largest':float(c.chg.abs().nlargest(2).iloc[1])}
json.dump(R,open('analysis/robustness.json','w'),indent=1,default=float); print(json.dumps(R,indent=1,default=float))
