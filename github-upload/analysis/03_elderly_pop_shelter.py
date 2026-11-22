import sys,glob,json,pandas as pd,geopandas as gpd
D=sys.argv[1];O=sys.argv[2]
cols=['남자 65~69세','남자 70세 이상','여자 65~69세','여자 70세 이상']
fs=sorted(glob.glob(f'{D}/250_LOCAL_RESD_2026*.csv'));print(len(fs),fs[0][-12:],fs[-1][-12:])
parts=[];star=0;tot=0
for f in fs:
    d=pd.read_csv(f,encoding='cp949',dtype=str,usecols=['일자','시간','250M격자','생활인구합계']+cols)
    d=d[d['시간'].str.strip()=='00']
    for c in cols:
        star+=(d[c].str.strip()=='*').sum();tot+=len(d)
        d[c]=pd.to_numeric(d[c].str.strip().replace('*','0'),errors='coerce').fillna(0)
    d['all']=pd.to_numeric(d['생활인구합계'],errors='coerce').fillna(0)
    d['old']=d[cols].sum(axis=1)
    parts.append(d.groupby(['일자','250M격자'])[['old','all']].sum().reset_index())
p=pd.concat(parts); print('* share',round(star/tot,3))
m=p.groupby('250M격자')[['old','all']].mean()  # mean over days (cells missing a day count as absent)
m=m.reindex(m.index); ndays=p.일자.nunique()
m=p.groupby('250M격자')[['old','all']].sum()/ndays
G=gpd.read_file(f'{D}/match.shp')
g=G.merge(m,left_on='CELL_ID',right_index=True,how='left').fillna({'old':0,'all':0})
print('grid',len(G),'matched',G.CELL_ID.isin(m.index).sum(),'pop cells not in grid',(~m.index.isin(G.CELL_ID)).sum())
g['share']=(g.old/g['all']).where(g['all']>0,0)
q=g.old.quantile(0.8);g['top20']=g.old>=q
print('seoul 65+ 00h',round(g.old.sum()),'all',round(g['all'].sum()),'q80',round(q,1),'top20',g.top20.sum(),'max',round(g.old.max()))
print(g.old.describe().round(1).to_dict())
o=g[['CELL_ID','old','share','top20','geometry']].copy();o['old']=o.old.round(1);o['share']=o.share.round(3)
o=o.to_crs(4326);open(f'{O}/heat_pop.geojson','w').write(o.to_json(drop_id=True))
json.dump({'q80':float(q),'top20':int(g.top20.sum()),'days':fs and [fs[0][-12:-4],fs[-1][-12:-4]],'ndays':int(ndays),'sum_old':float(g.old.sum()),'cells':len(g)},open(f'{O}/heat_stats.json','w'),ensure_ascii=False)
sh=pd.read_csv(f'{D}/서울시 무더위쉼터 (1).csv',encoding='cp949',dtype=str)
sh=gpd.GeoDataFrame(sh,geometry=gpd.points_from_xy(sh['경도'].astype(float),sh['위도'].astype(float)),crs=4326).to_crs(5179)
gb=g.geometry.bounds;g['ix']=(gb.minx//250).astype(int);g['iy']=(gb.miny//250).astype(int)
def cnt(pts):
    s={}
    for x,y in zip(pts.geometry.x,pts.geometry.y):
        k=(int(x//250),int(y//250));s[k]=s.get(k,0)+1
    return s
def n33(s,a,b): return sum(s.get((a+i,b+j),0) for i in(-1,0,1) for j in(-1,0,1))
ca=cnt(sh);co=cnt(sh[sh['시설구분2']!='회원이용시설'])
g['sh33']=[n33(ca,a,b) for a,b in zip(g.ix,g.iy)];g['sh33o']=[n33(co,a,b) for a,b in zip(g.ix,g.iy)]
t=g[g.top20];print('top20 no shelter3x3',(t.sh33==0).sum(),'no open shelter3x3',(t.sh33o==0).sum())
L=pd.read_csv(f'{O}/lst_cells.csv');g=g.merge(L,on='CELL_ID',how='left');g['hot']=g.hot.fillna(False).astype(bool)
g['both']=g.hot&g.top20
b=g[g.both];print('hot',g.hot.sum(),'both',len(b),'both no sh',(b.sh33==0).sum(),'both no open',(b.sh33o==0).sum())
o=g[['CELL_ID','old','top20','lst','hot','both','sh33','sh33o','geometry']].copy();o['old']=o.old.round(0).astype(int);o['lst']=o.lst.round(1)
o=o[o.lst.notna()].to_crs(4326);open(f'{O}/heat_pop.geojson','w').write(o.to_json(drop_id=True))
st=json.load(open(f'{O}/heat_stats.json'));st.update(hot=int(g.hot.sum()),both=int(len(b)),both_nosh=int((b.sh33==0).sum()),both_noopen=int((b.sh33o==0).sum()),noshelter=int((t.sh33==0).sum()),noopen=int((t.sh33o==0).sum()),cells_pos=len(o));json.dump(st,open(f'{O}/heat_stats.json','w'))
print(st)
