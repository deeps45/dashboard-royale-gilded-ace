"""Forecast daily floor coin-in. Train Jan-Apr, test May-Jun (time holdout, frozen before test).
Baseline: constant train mean. Model A: weekday mean. Model B: ridge on weekday + holiday + event flags (events are announced in advance)."""
import duckdb, numpy as np, pandas as pd, json
from sklearn.linear_model import Ridge
d=duckdb.sql("""select p.gaming_date::date gaming_date, p.coin_in_usd::double y, c.local_weekday wd, c.federal_holiday hol, c.scheduled_seconds/3600.0 hrs,
 p.events_active ev from 'data/1_prepared_views/property_day.parquet' p join 'data/2_machine_decision/calendar_day.parquet' c using(gaming_date) order by 1""").df()
ev=duckdb.sql("select * from 'data/4_context/events.parquet'").df()
d['gaming_date']=pd.to_datetime(d.gaming_date)
for c in ['start_date','end_date','announced_date']: ev[c]=pd.to_datetime(ev[c])
CUT=pd.Timestamp('2025-05-01')
for t in ['convention','sports_viewing','festival','property_promotion']:
    d['ev_'+t]=0
    for _,e in ev[(ev.event_type==t)&(ev.announced_date<CUT)].iterrows():
        d.loc[(d.gaming_date>=e.start_date)&(d.gaming_date<=e.end_date),'ev_'+t]=1
d['hol']=d.hol.notna().astype(int)
tr=d.gaming_date<CUT; te=~tr
base=np.full(te.sum(), d.y[tr].mean())
wdm=d[tr].groupby('wd').y.mean(); A=d.wd[te].map(wdm).values
X=pd.get_dummies(d.wd).astype(float).join(d[['hol','ev_convention','ev_sports_viewing','ev_festival','ev_property_promotion','hrs']])
B=Ridge(alpha=1.0).fit(X[tr],d.y[tr]).predict(X[te])
r=lambda p: float(np.mean(np.abs(d.y[te].values-p)))
res={'mae_baseline':r(base),'mae_weekday':r(A),'mae_ridge':r(B),'test_mean':float(d.y[te].mean())}
print({k:round(v) for k,v in res.items()})
print('weekday means (train):',wdm.round(-3).to_dict())
print('ridge coefs:',dict(zip(X.columns,Ridge(alpha=1.0).fit(X[tr],d.y[tr]).coef_.round(-2))))
# fit on all 6 months for July planning (weekday only)
wd_all=d.groupby('wd').y.mean()
d['pred_baseline']=d.y[tr].mean(); d['pred_weekday']=d.wd.map(wdm); d.loc[te,'pred_ridge']=B; d.loc[tr,'pred_ridge']=Ridge(alpha=1.0).fit(X[tr],d.y[tr]).predict(X[tr])
d['split']=np.where(tr,'train','test')
d[['gaming_date','y','pred_baseline','pred_weekday','pred_ridge','split']].assign(gaming_date=lambda x:x.gaming_date.dt.strftime('%Y-%m-%d')).to_json('analysis/model_preds.json',orient='records')
json.dump({**res,'weekday_means_train':wdm.to_dict(),'weekday_means_all':wd_all.to_dict()},open('analysis/model_summary.json','w'))
