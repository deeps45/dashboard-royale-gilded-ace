"""Model v3: wider candidate set, same honest protocol.
- Selection: rolling-origin CV inside Jan-Apr only (5 folds x 14 days, same folds as model2). May-Jun is scored once, after selection.
- Inputs are only what is known on the forecast date: calendar, holidays, events announced before the cutoff, and the floor's
  own level in the 28 days before the cutoff. No weather, tourism or survey data (published later), no holdout-day lags.
- Interval: weekday-scaled split-conformal from CV residuals (Fri/Sat swing more than Tuesdays).
Writes analysis/model3.json (same schema as model2.json; the dashboard reads this one)."""
import duckdb, numpy as np, pandas as pd, json
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor

d = duckdb.sql("""select p.gaming_date::date gd, p.coin_in_usd::double y, c.local_weekday wd, c.federal_holiday hol, c.scheduled_seconds/3600.0 hrs
 from 'data/1_prepared_views/property_day.parquet' p join 'data/2_machine_decision/calendar_day.parquet' c using(gaming_date) order by 1""").df()
d['gd'] = pd.to_datetime(d.gd); d['hol'] = d.hol.notna().astype(int)
ev = duckdb.sql("select * from 'data/4_context/events.parquet'").df()
for c in ['start_date', 'end_date', 'announced_date']: ev[c] = pd.to_datetime(ev[c])
WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']; ETYPES = ['convention', 'sports_viewing', 'festival', 'property_promotion']

def feats(df, cutoff):
    X = pd.DataFrame({w: (df.wd == w).astype(float) for w in WD}, index=df.index)
    X['hol'] = df.hol.values; X['prehol'] = df.hol.shift(-1, fill_value=0).values  # holidays are on the calendar in advance
    X['hrs'] = df.hrs.values; X['wkend'] = df.wd.isin(['Fri', 'Sat']).astype(float)
    for t in ETYPES:
        X['ev_' + t] = 0.0
        for _, e in ev[(ev.event_type == t) & (ev.announced_date < cutoff)].iterrows():
            X.loc[((df.gd >= e.start_date) & (df.gd <= e.end_date)).values, 'ev_' + t] = 1.0
    X['ev_any'] = X[['ev_' + t for t in ETYPES]].max(axis=1)
    return X

def wd_profile(tr, half_life=None):
    """Weekday means; optionally recency-weighted (exponential decay in days before the cutoff)."""
    w = np.ones(len(tr)) if half_life is None else 0.5 ** ((tr.gd.max() - tr.gd).dt.days.values / half_life)
    return (tr.assign(w=w, yw=tr.y * w).groupby('wd')[['yw', 'w']].sum().pipe(lambda g: g.yw / g.w))

def event_lifts(tr, Xtr):
    """Multiplicative lift per event type, estimated on training days vs the weekday profile."""
    base = tr.wd.map(wd_profile(tr)).values; r = tr.y.values / base; lifts = {}
    for t in ETYPES + ['hol', 'prehol']:
        col = Xtr['ev_' + t] if t in ETYPES else Xtr[t]
        m = col.values == 1; lifts[t] = float(np.mean(r[m])) if m.sum() >= 2 else 1.0
    return lifts

def mult(tr, te, Xtr, Xte, half_life=None, level=False):
    prof = wd_profile(tr, half_life); p = te.wd.map(prof).values.astype(float); L = event_lifts(tr, Xtr)
    for t in ETYPES: p = np.where(Xte['ev_' + t] == 1, p * L[t], p)
    p = np.where(Xte.hol == 1, p * L['hol'], np.where(Xte.prehol == 1, p * L['prehol'], p))
    if level:  # recent level: last 28 training days vs what the profile expected for them (known at the cutoff)
        last = tr[tr.gd > tr.gd.max() - pd.Timedelta(days=28)]
        ratio = last.y.sum() / last.wd.map(prof).sum(); p = p * (1 + 0.5 * (ratio - 1))  # shrink halfway to 1
    return p

GBM_GRID = [(150, 2, 0.05), (300, 2, 0.03), (200, 3, 0.03)]
def fit_predict(name, tr, te, cutoff):
    Xtr, Xte = feats(tr, cutoff), feats(te, cutoff); y = tr.y.values
    base_cols = WD + ['hol', 'hrs'] + ['ev_' + t for t in ETYPES]  # model2 feature set
    if name == 'Constant mean': return np.full(len(te), y.mean())
    if name == 'Weekday mean': return te.wd.map(tr.groupby('wd').y.mean()).values
    if name == 'Weekday median': return te.wd.map(tr.groupby('wd').y.median()).values
    if name == 'Ridge': return Ridge(alpha=1).fit(Xtr[base_cols], y).predict(Xte[base_cols])
    if name == 'Ridge + trend':
        Xa, Xb = Xtr[base_cols].assign(t=(tr.gd - pd.Timestamp('2025-01-01')).dt.days.values / 30), Xte[base_cols].assign(t=(te.gd - pd.Timestamp('2025-01-01')).dt.days.values / 30)
        return Ridge(alpha=1).fit(Xa, y).predict(Xb)
    if name == 'Gradient boosting': return GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, random_state=0).fit(Xtr[base_cols], y).predict(Xte[base_cols])
    if name == 'Weekday × event lifts': return mult(tr, te, Xtr, Xte)
    if name == 'Recency-weighted weekday × lifts': return mult(tr, te, Xtr, Xte, half_life=42)
    if name == 'Weekday × lifts + recent level': return mult(tr, te, Xtr, Xte, level=True)
    if name == 'Boosting, richer calendar (tuned)':
        cols = list(Xtr.columns); preds = []
        for n, dep, lr in GBM_GRID: preds.append(GradientBoostingRegressor(n_estimators=n, max_depth=dep, learning_rate=lr, random_state=0, loss='absolute_error').fit(Xtr[cols], y).predict(Xte[cols]))
        return np.mean(preds, axis=0)  # small bag over the grid instead of picking one setting (no extra selection step)
    if name == 'Ensemble: boosting + weekday × lifts':
        return 0.5 * fit_predict('Gradient boosting', tr, te, cutoff) + 0.5 * mult(tr, te, Xtr, Xte)
    if name == 'Ensemble: richer boosting + weekday × lifts':
        return 0.5 * fit_predict('Boosting, richer calendar (tuned)', tr, te, cutoff) + 0.5 * mult(tr, te, Xtr, Xte)

V2 = ['Constant mean', 'Weekday mean', 'Weekday median', 'Ridge', 'Ridge + trend', 'Gradient boosting']
V3 = ['Weekday × event lifts', 'Recency-weighted weekday × lifts', 'Weekday × lifts + recent level', 'Boosting, richer calendar (tuned)',
      'Ensemble: boosting + weekday × lifts', 'Ensemble: richer boosting + weekday × lifts']
NAMES = V2 + V3
train = d[d.gd < '2025-05-01'].reset_index(drop=True); test = d[d.gd >= '2025-05-01'].reset_index(drop=True); CUT = pd.Timestamp('2025-05-01')
cv = {n: [] for n in NAMES}; res = {n: [] for n in NAMES}; reswd = {n: [] for n in NAMES}
for start in pd.date_range('2025-02-15', '2025-04-17', freq='14D'):
    tr = train[train.gd < start].reset_index(drop=True); va = train[(train.gd >= start) & (train.gd < start + pd.Timedelta(days=14))].reset_index(drop=True)
    for n in NAMES:
        p = fit_predict(n, tr, va, start); cv[n].append(float(np.abs(va.y.values - p).mean()))
        res[n] += list(va.y.values - p); reswd[n] += list(va.wd.values)
cvm = {n: float(np.mean(v)) for n, v in cv.items()}; best = min(cvm, key=cvm.get)
print('selected by CV (before looking at May-Jun):', best)

# --- one-time holdout scoring ---
testp = {n: fit_predict(n, train, test, CUT) for n in NAMES}
testm = {n: float(np.abs(test.y.values - testp[n]).mean()) for n in NAMES}
bias = {n: float(np.mean(test.y.values - testp[n])) for n in NAMES}
for n in NAMES: print(f"{n:45s} CV-MAE {cvm[n]:>9,.0f}  test-MAE {testm[n]:>9,.0f}  test bias {bias[n]:>+9,.0f}")

# --- weekday-scaled split-conformal 80% interval from CV residuals of the selected model ---
r = pd.DataFrame({'r': res[best], 'wd': reswd[best]})
scale = r.groupby('wd').r.apply(lambda s: np.sqrt(np.mean(s ** 2))); scale = scale / scale.mean()
qn = float(np.quantile(np.abs(r.r / r.wd.map(scale)), 0.8 * (1 + 1 / len(r))))  # finite-sample conformal quantile
pt = testp[best]; half = qn * test.wd.map(scale).values
cover = float(np.mean(np.abs(test.y.values - pt) <= half))
sym = float(np.percentile(np.abs(res[best]), 80)); cover_sym = float(np.mean(np.abs(test.y.values - pt) <= sym))
print(f'80% interval: weekday-scaled coverage {cover:.2f} (symmetric {cover_sym:.2f})')

# --- July forecast (refit on all 6 months; no July events in the table) ---
jul = pd.DataFrame({'gd': pd.date_range('2025-07-01', '2025-07-30')}); jul['wd'] = jul.gd.dt.strftime('%a')
jul['hol'] = (jul.gd == '2025-07-04').astype(int); jul['hrs'] = 24.0; jul['y'] = np.nan
pj = fit_predict(best, d, jul, pd.Timestamp('2025-07-01')); hj = qn * jul.wd.map(scale).values
ptr = fit_predict(best, train, train, CUT); htr = qn * train.wd.map(scale).values
preds = []
for df, p, h, split in [(train, ptr, htr, 'train'), (test, pt, half, 'test'), (jul, pj, hj, 'forecast')]:
    for i in range(len(df)):
        preds.append({'d': df.gd.iloc[i].strftime('%Y-%m-%d'), 'y': None if pd.isna(df.y.iloc[i]) else float(df.y.iloc[i]), 'p': float(p[i]),
                      'lo': float(p[i] - h[i]), 'hi': float(p[i] + h[i]), 'base': float(train.y.mean()), 'split': split})
# error by weekday on the holdout (selected vs baseline), for the dashboard
ewd = pd.DataFrame({'wd': test.wd, 'sel': np.abs(test.y - pt), 'base': np.abs(test.y - train.y.mean())}).groupby('wd').mean().reindex(WD)
out = {'cv': cvm, 'cv_folds': cv, 'test': testm, 'bias': bias, 'selected': best, 'v2_selected': 'Gradient boosting', 'new_in_v3': V3,
       'q10': -sym, 'q90': sym, 'coverage': cover, 'coverage_symmetric': cover_sym, 'interval': 'weekday-scaled split-conformal',
       'scale_wd': scale.reindex(WD).round(3).to_dict(), 'qn': qn, 'err_wd': {k: ewd[k].round(0).tolist() for k in ['sel', 'base']},
       'preds': preds, 'jul_by_wd': pd.Series(pj, index=jul.wd).groupby(level=0).mean().to_dict(),
       'jul_total': float(pj.sum()), 'improve_vs_base': 1 - testm[best] / testm['Constant mean']}
json.dump(out, open('analysis/model3.json', 'w'))

# --- is the v3 pick really different from v2? Paired block bootstrap by week over the 61 holdout days ---
rng = np.random.default_rng(0); wk = ((test.gd - test.gd.min()).dt.days // 7).values; W = np.unique(wk)
ae = {n: np.abs(test.y.values - testp[n]) for n in ['Gradient boosting', best, 'Constant mean']}
boot = {k: [] for k in ['v2', 'v3', 'diff', 'base']}
for _ in range(4000):
    idx = np.concatenate([np.where(wk == w)[0] for w in rng.choice(W, len(W))])
    v2_, v3_ = ae['Gradient boosting'][idx].mean(), ae[best][idx].mean()
    boot['v2'].append(v2_); boot['v3'].append(v3_); boot['diff'].append(v3_ - v2_); boot['base'].append(ae['Constant mean'][idx].mean())
ci = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in boot.items()}
p_worse = float(np.mean(np.array(boot['diff']) <= 0))
# same weekday-scaled interval applied to the frozen v2 model (calibrated on its own CV residuals)
r2 = pd.DataFrame({'r': res['Gradient boosting'], 'wd': reswd['Gradient boosting']})
s2 = r2.groupby('wd').r.apply(lambda s: np.sqrt(np.mean(s ** 2))); s2 = s2 / s2.mean()
q2 = float(np.quantile(np.abs(r2.r / r2.wd.map(s2)), 0.8 * (1 + 1 / len(r2))))
cov2 = float(np.mean(np.abs(test.y.values - testp['Gradient boosting']) <= q2 * test.wd.map(s2).values))
cov2_sym = float(np.mean(np.abs(test.y.values - testp['Gradient boosting']) <= np.percentile(np.abs(res['Gradient boosting']), 80)))
out.update(ci=ci, p_v3_not_worse=p_worse, v2_interval={'weekday_scaled_coverage': cov2, 'symmetric_coverage': cov2_sym, 'qn': q2, 'scale_wd': s2.reindex(WD).round(3).to_dict()})
json.dump(out, open('analysis/model3.json', 'w'))
print('95% CI MAE  v2', [round(x) for x in ci['v2']], ' v3', [round(x) for x in ci['v3']], ' baseline', [round(x) for x in ci['base']], ' v3-v2', [round(x) for x in ci['diff']], ' P(v3<=v2)', round(p_worse, 3))
print(f'v2 interval coverage: symmetric {cov2_sym:.2f} -> weekday-scaled {cov2:.2f}')
