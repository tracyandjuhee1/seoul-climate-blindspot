import sys,json,numpy as np,rasterio,geopandas as gpd
from rasterio.features import rasterize
D=sys.argv[1];O=sys.argv[2]
r=rasterio.open(f'{D}/Seoul_LST_Summer2026.tif');print(r.crs,r.res,r.shape,r.bounds)
a=r.read(1).astype(float);nd=r.nodata
if nd is not None:a[a==nd]=np.nan
print('valid',np.isfinite(a).mean().round(3),np.nanpercentile(a,[1,50,99]).round(1))
G=gpd.read_file(f'{D}/match.shp').to_crs(r.crs)
lab=rasterize(((g,i+1) for i,g in enumerate(G.geometry)),out_shape=a.shape,transform=r.transform,fill=0,dtype='int32')
med=np.full(len(G),np.nan);cov=np.zeros(len(G))
idx=lab.ravel();v=a.ravel()
order=np.argsort(idx,kind='stable');idx_s=idx[order];v_s=v[order]
bounds=np.searchsorted(idx_s,np.arange(1,len(G)+2))
for i in range(len(G)):
    s=v_s[bounds[i]:bounds[i+1]];f=s[np.isfinite(s)]
    if len(s):cov[i]=len(f)/len(s)
    if len(f)>=10:med[i]=np.median(f)
G['lst']=med;G['cov']=cov
print('cells with lst',np.isfinite(med).sum(),'of',len(G))
q=np.nanquantile(med,0.8);G['hot']=G.lst>=q;print('q80',round(q,2),'hot',G.hot.sum(), 'pct',np.nanpercentile(med,[5,50,95]).round(1))
json.dump({'q80':float(q),'hot':int(G.hot.sum()),'n':int(np.isfinite(med).sum()),'p5':float(np.nanpercentile(med,5)),'p95':float(np.nanpercentile(med,95))},open(f'{O}/lst_stats.json','w'))
G[['CELL_ID','lst','hot']].to_csv(f'{O}/lst_cells.csv',index=False)
