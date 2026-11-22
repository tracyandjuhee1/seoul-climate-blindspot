import sys, json, numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import box
from shapely.ops import unary_union
D=sys.argv[1]; O=sys.argv[2]
bands=[]
for i in range(1,7):
    g=gpd.read_file(f'{D}/DS_FLOODING_{i}.shp',encoding='cp949').set_crs(5186,allow_override=True).to_crs(5179)
    g['geometry']=g.buffer(0)
    bands.append(unary_union(g.geometry))
# deep first
clean=[None]*6; deeper=None
for i in range(5,-1,-1):
    geom=bands[i] if deeper is None else bands[i].difference(deeper)
    clean[i]=geom; deeper=bands[i] if deeper is None else deeper.union(bands[i])
labels=['0.5m 미만','0.5~1.0m','1.0~2.0m','2.0~3.0m','3.0m 이상','3.0m 이상'] # placeholder
fl=gpd.GeoDataFrame({'band':list(range(1,7))},geometry=clean,crs=5179)
print('areas km2',[round(a/1e6,2) for a in fl.area], 'union',round(deeper.area/1e6,2))
# grid
x0,y0,x1,y1=deeper.bounds
xs=np.arange(np.floor(x0/250)*250,x1,250); ys=np.arange(np.floor(y0/250)*250,y1,250)
cells=gpd.GeoDataFrame(geometry=[box(x,y,x+250,y+250) for x in xs for y in ys],crs=5179)
cells['ix']=[int(x//250) for x in xs for y in ys]; cells['iy']=[int(y//250) for x in xs for y in ys]
inter=gpd.overlay(cells,gpd.GeoDataFrame(geometry=[deeper],crs=5179),how='intersection')
inter['ratio']=inter.area/62500
fc=cells.merge(inter[['ix','iy','ratio']],on=['ix','iy'])
fc=fc[fc.ratio>0].copy()
G=gpd.read_file(f'{D}/match.shp'); gb=G.geometry.bounds
G['ix']=(gb.minx//250).astype(int); G['iy']=(gb.miny//250).astype(int)
n0=len(fc); fc=fc.merge(G[['ix','iy','CELL_ID']],on=['ix','iy']); print('official grid clip',n0,'->',len(fc))
print('flood cells',len(fc),'max ratio',fc.ratio.max())
q=fc.ratio.quantile(0.8); fc['top20']=fc.ratio>=q; print('q80',q, fc.top20.sum())
# facilities
sh=pd.read_csv(f'{D}/서울시 무더위쉼터 (1).csv',encoding='cp949',dtype=str)
sh=gpd.GeoDataFrame(sh,geometry=gpd.points_from_xy(sh['경도'].astype(float),sh['위도'].astype(float)),crs=4326)
ev=pd.read_csv(f'{D}/서울시 이재민임시주거시설(지진겸용).csv',encoding='cp949',dtype=str)
ev['_x']=ev['경도'].astype(float);ev['_y']=ev['위도'].astype(float)
print('ev total',len(ev));ev=ev[ev._x.between(126.76,127.19)&ev._y.between(37.41,37.72)].copy();print('ev valid',len(ev))
ev=gpd.GeoDataFrame(ev,geometry=gpd.points_from_xy(ev['경도'].astype(float),ev['위도'].astype(float)),crs=4326)
def cnt(pts):
    p=pts.to_crs(5179); s={}
    for x,y in zip(p.geometry.x,p.geometry.y):
        k=(int(x//250),int(y//250)); s[k]=s.get(k,0)+1
    return s
def n33(s,ix,iy): return sum(s.get((ix+a,iy+b),0) for a in(-1,0,1) for b in(-1,0,1))
evc=cnt(ev)
inflood=ev.to_crs(5179).within(deeper); print('ev in flood',inflood.sum())
evc_out=cnt(ev[~inflood.values])
fc['ev_in']=[evc.get((a,b),0) for a,b in zip(fc.ix,fc.iy)]
fc['ev33']=[n33(evc,a,b) for a,b in zip(fc.ix,fc.iy)]
fc['ev33_out']=[n33(evc_out,a,b) for a,b in zip(fc.ix,fc.iy)]
t=fc[fc.top20]; print('top20 no ev in cell',(t.ev_in==0).sum(),'no ev 3x3',(t.ev33==0).sum(),'no out-of-zone ev 3x3',(t.ev33_out==0).sum())
# exports
def wr(g,name,prec=5):
    g=g.to_crs(4326); open(f'{O}/{name}','w').write(g.to_json(drop_id=True,to_wgs84=False).replace(' ',''))
fl4=fl.copy(); fl4['geometry']=fl4.simplify(8)
fl4=fl4[~fl4.is_empty]
wr(fl4,'flood.geojson')
fc2=fc[['CELL_ID','ratio','top20','ev_in','ev33','ev33_out','geometry']].copy(); fc2['ratio']=fc2.ratio.round(3)
wr(fc2,'flood_cells.geojson')
evo=ev[['수용시설명','geometry']].rename(columns={'수용시설명':'n'}); evo['inz']=inflood.values.astype(int)
wr(evo,'evac.geojson')
sh['open']=(sh['시설구분2']!='회원이용시설').astype(int)
sh['h']=sh['기본운영_요일'].fillna('')+' '+sh['기본운영_시작시간'].fillna('')+'~'+sh['기본운영_종료시간'].fillna('')
sho=sh[['쉼터명칭','시설구분2','h','open','geometry']].rename(columns={'쉼터명칭':'n','시설구분2':'t'})
wr(sho,'shelter.geojson')
print(sh['시설구분2'].value_counts().to_dict()); print(sh['시설구분1'].value_counts().to_dict())
json.dump({'q80':float(q),'cells':int(len(fc)),'top20':int(fc.top20.sum()),'top20_noev33':int((t.ev33==0).sum()),'top20_noev33_out':int((t.ev33_out==0).sum()),'ev_inflood':int(inflood.sum())},open(f'{O}/stats.json','w'))
