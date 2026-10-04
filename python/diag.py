import pandas as pd, numpy as np
from bulletin import ihpc, table
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',500)
A=pd.read_pickle('all.pkl'); eden=A['eden']; fcp=A['fao_cp']; M=A['MONTHS']; ISO=A['ISO']; monde=A['monde']
# 1. EDEN vs bulletin
b=ihpc()
b['eden_all']=[eden.loc[d,(i,'cpi_all')] for i,d in zip(b.iso3,b.date)]
b['eden_food']=[eden.loc[d,(i,'cpi_food')] for i,d in zip(b.iso3,b.date)]
b['d_all']=b.eden_all-b.ihpc_global; b['d_food']=b.eden_food-b.ihpc_div1
print('EDEN vs bulletin: n',len(b),'max|d_all|',b.d_all.abs().max(),'max|d_food|',b.d_food.abs().max())
print(b[(b.d_all.abs()>0.051)|(b.d_food.abs()>0.051)])
b.to_pickle('bull_ihpc.pkl')
usd=table('Tableau 9.3 Taux de change bilatéraux',0)
x=(655.957/monde.eur_usd).reindex(usd.index)
print('usd_xof: max abs % diff vs bulletin', (100*(x/usd-1)).abs().max())
oil=table('Tableau 9.4 Cours mondiaux',5); print((100*(monde.oil_usd.reindex(oil.index)/oil-1)).round(1).to_dict())
pd.to_pickle(dict(usd=usd,oil=oil,imp=table('Tableau 9.5 Produits alimentaires',5)),'bull_tabs.pkl')
# 2. EDEN vs FAOSTAT : ratio stability & m/m difference
print('\n=== EDEN vs FAOSTAT')
res=[]
for iso in ISO:
    for v in ['cpi_all','cpi_food']:
        e=eden[(iso,v)].reindex(M); f=fcp[(iso,v+'_alt')].reindex(M)
        r=(f/e)
        de=100*np.log(e).diff(); df=100*np.log(f).diff(); dd=(df-de)
        for per,(a,z) in {'2000-2024':('2000-01','2024-12'),'2025-2026':('2025-01','2026-09')}.items():
            rr=r.loc[a:z].dropna(); d2=dd.loc[a:z].dropna()
            res.append((iso,v,per,len(rr),rr.mean(),rr.std()/rr.mean()*100,rr.min(),rr.max(),d2.abs().max(),(d2.abs()>0.5).sum(), np.corrcoef(de.loc[d2.index],df.loc[d2.index])[0,1]))
R=pd.DataFrame(res,columns=['iso','var','per','n','ratio_mean','ratio_cv%','rmin','rmax','max|dmm|','n>0.5pt','corr_mm'])
print(R.round(3).to_string())
R.to_pickle('diag_alt.pkl')
# ratio around 2024-12 / 2025-01
for iso in ISO:
    for v in ['cpi_all','cpi_food']:
        r=(fcp[(iso,v+'_alt')]/eden[(iso,v)]).reindex(M)
        print(iso,v,'ratio',' '.join(f'{d[2:]}:{r[d]:.4f}' for d in ['2000-01','2008-01','2014-12','2015-06','2023-06','2024-10','2024-11','2024-12','2025-01','2025-02','2025-06','2025-12','2026-03'] if d in r.index))
