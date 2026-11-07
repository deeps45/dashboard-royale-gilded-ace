"""Model selection by rolling-origin CV inside Jan-Apr only; May-Jun test touched once at the end.
Candidates: constant mean, weekday mean, weekday median, ridge (weekday+holiday+announced events+hours), ridge + linear trend, gradient boosting.
Also: 80% prediction interval from CV residuals, and a July 2025 forecast for staffing/promo planning."""
import duckdb, numpy as np, pandas as pd, json
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
d=duckdb.sql("""select p.gaming_date::date gd, p.coin_in_usd::double y, c.local_weekday wd, c.federal_holiday hol, c.scheduled_seconds/3600.0 hrs
 from 'data/1_prepared_views/property_day.parquet' p join 'data/2_machine_decision/calendar_day.parquet' c using(gaming_date) order by 1""").df()
d['gd']=pd.to_datetime(d.gd); d['hol']=d.hol.notna().astype(int)
ev=duckdb.sql("select * from 'data/4_context/events.parquet'").df()
for c in ['start_date','end_date','announced_date']: ev[c]=pd.to_datetime(ev[c])
WD=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
def feats(df, cutoff):
    X=pd.DataFrame({w:(df.wd==w).astype(float) for w in WD},index=df.index)
    X['hol']=df.hol; X['hrs']=df.hrs; X['t']=(df.gd-pd.Timestamp('2025-01-01')).dt.days/30
    for t in ['convention','sports_viewing','festival','property_promotion']:
        X['ev_'+t]=0.0
        for _,e in ev[(ev.event_type==t)&(ev.announced_date<cutoff)].iterrows():
            X.loc[(df.gd>=e.start_date)&(df.gd<=e.end_date),'ev_'+t]=1.0
    return X
def fit_predict(name, tr, te, cutoff):
    Xtr,Xte=feats(tr,cutoff),feats(te,cutoff); y=tr.y
    if name=='Constant mean': return np.full(len(te),y.mean())
    if name=='Weekday mean': return te.wd.map(tr.groupby('wd').y.mean()).values
    if name=='Weekday median': return te.wd.map(tr.groupby('wd').y.median()).values
    cols=[c for c in Xtr.columns if c!='t']
    if name=='Ridge': return Ridge(alpha=1).fit(Xtr[cols],y).predict(Xte[cols])
    if name=='Ridge + trend': return Ridge(alpha=1).fit(Xtr,y).predict(Xte)
    if name=='Gradient boosting': return GradientBoostingRegressor(n_estimators=200,max_depth=2,learning_rate=0.05,random_state=0).fit(Xtr[cols],y).predict(Xte[cols])
NAMES=['Constant mean','Weekday mean','Weekday median','Ridge','Ridge + trend','Gradient boosting']
train=d[d.gd<'2025-05-01'].reset_index(drop=True); test=d[d.gd>='2025-05-01'].reset_index(drop=True)
# rolling origin: train up to fold start, predict next 14 days; folds start Feb 15 .. Apr 17
cv={n:[] for n in NAMES}; res={n:[] for n in NAMES}
for start in pd.date_range('2025-02-15','2025-04-17',freq='14D'):
    tr=train[train.gd<start]; va=train[(train.gd>=start)&(train.gd<start+pd.Timedelta(days=14))]
    for n in NAMES:
        p=fit_predict(n,tr,va,start); cv[n].append(np.abs(va.y.values-p).mean())
        res[n]+=list(va.y.values-p)
cvm={n:float(np.mean(v)) for n,v in cv.items()}; best=min(cvm,key=cvm.get)
cut=pd.Timestamp('2025-05-01'); testm={n:float(np.abs(test.y.values-fit_predict(n,train,test,cut)).mean()) for n in NAMES}
for n in NAMES: print(f"{n:18s} CV-MAE {cvm[n]:>9,.0f}   test-MAE {testm[n]:>9,.0f}")
print('selected by CV:',best)
a80=np.percentile(np.abs(res[best]),80); q10,q90=-a80,a80; pt=fit_predict(best,train,test,cut); cover=float(np.mean((test.y.values>=pt+q10)&(test.y.values<=pt+q90)))
print('80% interval',round(q10),round(q90),'test coverage',round(cover,2))
# July forecast: refit on all 6 months with selected model, events known by Jul 1 (none in July in table)
jul=pd.DataFrame({'gd':pd.date_range('2025-07-01','2025-07-30')}); jul['wd']=jul.gd.dt.strftime('%a'); jul['hol']=(jul.gd=='2025-07-04').astype(int); jul['hrs']=24.0; jul['y']=np.nan
pj=fit_predict(best,d,jul,pd.Timestamp('2025-07-01'))
preds=[]
for df,p,split in [(train,fit_predict(best,train,train,cut),'train'),(test,pt,'test'),(jul,pj,'forecast')]:
    for i in range(len(df)): preds.append({'d':df.gd.iloc[i].strftime('%Y-%m-%d'),'y':None if pd.isna(df.y.iloc[i]) else float(df.y.iloc[i]),'p':float(p[i]),'lo':float(p[i]+q10),'hi':float(p[i]+q90),'base':float(train.y.mean()),'split':split})
json.dump({'cv':cvm,'test':testm,'selected':best,'q10':q10,'q90':q90,'coverage':cover,'preds':preds,'jul_by_wd':pd.Series(pj,index=jul.wd).groupby(level=0).mean().to_dict()},open('analysis/model2.json','w'))
