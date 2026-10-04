"""Extraction et harmonisation de toutes les sources -> pickles + diagnostics."""
import pandas as pd, numpy as np, openpyxl, re, subprocess
from parse_eden import parse
ISO=['BEN','BFA','CIV','GNB','MLI','NER','SEN','TGO']
MONTHS=list(pd.period_range('2000-01','2026-09',freq='M').strftime('%Y-%m'))
# ---------- EDEN
d=pd.concat([parse('exportIndicateurs.csv'),parse('exportIndicateurs_1.csv')],ignore_index=True)
d['var']=d.libelle.map({'Indice des prix a la consommation':'cpi_all','Indice des prix de la fonction alimentation':'cpi_food'})
assert d.duplicated(['iso3','var','date']).sum()==0
eden=d.pivot(index='date',columns=['iso3','var'],values='value')
# ---------- FAOSTAT CP
MN={m:i+1 for i,m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'])}
A2I={'Benin':'BEN','Burkina Faso':'BFA',"Côte d'Ivoire":'CIV','Guinea-Bissau':'GNB','Mali':'MLI','Niger':'NER','Senegal':'SEN','Togo':'TGO'}
f=pd.read_csv('FAOSTAT_data_en_10-4-2026.csv')
f['date']=f.Year.astype(str)+'-'+f.Months.map(MN).astype(str).str.zfill(2); f['iso3']=f.Area.map(A2I)
f['var']=f['Item Code'].map({23012:'cpi_all_alt',23013:'cpi_food_alt'})
assert f.duplicated(['iso3','var','date']).sum()==0
fao_cp=f.pivot(index='date',columns=['iso3','var'],values='Value'); fao_fl=f.pivot(index='date',columns=['iso3','var'],values='Flag')
# ---------- FAO FPI
p=pd.read_csv('food_price_indices_data.csv',skiprows=2).dropna(axis=1,how='all').dropna(how='all')
p=p[['Date','Food Price Index','Meat','Dairy','Cereals','Oils','Sugar']].rename(columns={'Date':'date','Food Price Index':'fao_food','Meat':'fao_meat','Dairy':'fao_dairy','Cereals':'fao_cereals','Oils':'fao_oils','Sugar':'fao_sugar'}).set_index('date')
assert p.index.is_unique
# ---------- Pink Sheet
wb=openpyxl.load_workbook('CMO-Historical-Data-Monthly.xlsx',data_only=True); ws=wb['Monthly Prices']
hdr=[ws.cell(5,c).value for c in range(1,ws.max_column+1)]
want={'Crude oil, Brent':'oil_usd','Rice, Thai 5% ':'rice_thai','Wheat, US HRW':'wheat_hrw','Palm oil':'palm_oil','Sugar, world':'sugar_world','Maize':'maize'}
rows=[]
for r in range(7,ws.max_row+1):
    per=ws.cell(r,1).value
    if not per: continue
    m=re.match(r'(\d{4})M(\d{2})$',per); assert m,per
    rec={'date':f'{m.group(1)}-{m.group(2)}'}
    for k,v in want.items():
        x=ws.cell(r,hdr.index(k)+1).value
        rec[v]=float(x) if isinstance(x,(int,float)) else np.nan
    rows.append(rec)
pink=pd.DataFrame(rows).set_index('date'); assert pink.index.is_unique
pink_units={v:ws.cell(6,hdr.index(k)+1).value for k,v in want.items()}
# ---------- ECB
e=pd.read_csv('ECB_Data_Portal_20261004111939.csv'); e.columns=['d','tp','eur_usd']; e['date']=e.d.str[:7]
ecb=e.set_index('date')[['eur_usd']]; assert ecb.index.is_unique
# ---------- GSCPI
wb2=openpyxl.load_workbook('gscpi_data.xlsx',data_only=True); ws2=wb2['GSCPI Monthly Data']
g=[(ws2.cell(r,1).value,ws2.cell(r,2).value) for r in range(6,ws2.max_row+1) if ws2.cell(r,1).value]
g=pd.DataFrame(g,columns=['d','gscpi']); g['date']=pd.to_datetime(g.d,format='%d-%b-%Y').dt.strftime('%Y-%m'); gs=g.set_index('date')[['gscpi']]; assert gs.index.is_unique
# ---------- BCEAO Tableau 9.5 (lu dans le PDF, vérifié visuellement page 32 du PDF)
t95={'2024-10':136.97,'2024-11':142.24,'2024-12':142.21,'2025-01':141.43,'2025-02':139.52,'2025-03':132.36,'2025-04':125.84,'2025-05':123.04,'2025-06':125.33,'2025-07':117.99,'2025-08':116.62,'2025-09':110.34,'2025-10':105.66,'2025-11':103.04,'2025-12':102.74,'2026-01':102.01,'2026-02':103.77,'2026-03':111.56}
bimp=pd.Series(t95,name='bceao_import_food')
# ---------- Monde
monde=pd.DataFrame(index=MONTHS)
monde=monde.join(p).join(pink).join(ecb).join(gs).join(bimp)
monde['cpi_all_umoa']=eden[('UMOA','cpi_all')].reindex(MONTHS); monde['cpi_food_umoa']=eden[('UMOA','cpi_food')].reindex(MONTHS)
# ---------- Annuel
q=pd.read_csv('FAOSTAT_data_en_10-4-2026_2.csv',dtype={'Item Code (CPC)':str})
c=q[(q.Item=='Cereals, primary')&(q.Element=='Production')].copy(); c['iso3']=c.Area.map(A2I); assert (c.Unit=='t').all()
prod=c.pivot(index='Year',columns='iso3',values='Value'); prod_fl=c.pivot(index='Year',columns='iso3',values='Flag')
s=pd.read_csv('FAOSTAT_data_en_10-4-2026_1.csv'); s['iso3']=s.Area.map(A2I)
assert (s.Item=='Cereal import dependency ratio (percent) (3-year average)').all()
s['center']=s.Year.str[:4].astype(int)+1
dep=s.pivot(index='center',columns='iso3',values='Value'); dep_fl=s.pivot(index='center',columns='iso3',values='Flag')
w=pd.read_csv('API_TM.VAL.FOOD.ZS.UN_DS2_en_csv_v2_404666.csv',skiprows=4); w=w[w['Country Code'].isin(ISO)]
assert (w['Indicator Code']=='TM.VAL.FOOD.ZS.UN').all()
fis=w.set_index('Country Code')[[str(y) for y in range(2000,2026)]].T; fis.index=fis.index.astype(int)
YEARS=list(range(2000,2027))
annuel={'local_agri_supply':prod.reindex(YEARS)[ISO],'local_agri_supply_flag':prod_fl.reindex(YEARS)[ISO],'import_dependency':dep.reindex(YEARS)[ISO],'import_dependency_flag':dep_fl.reindex(YEARS)[ISO],'food_imports_share':fis.reindex(YEARS)[ISO]}
pd.to_pickle(dict(eden=eden,fao_cp=fao_cp,fao_fl=fao_fl,monde=monde,annuel=annuel,pink_units=pink_units,MONTHS=MONTHS,ISO=ISO,YEARS=YEARS,eden_long=d),'all.pkl')
if __name__=='__main__':
    pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',400)
    print(pink_units)
    cov=pd.DataFrame({c:[monde[c].first_valid_index(),monde[c].last_valid_index(),monde[c].notna().sum(),monde[c].isna().sum(),(monde[c]==0).sum(),monde[c].min(),monde[c].max()] for c in monde},index=['first','last','n','miss','zeros','min','max']).T
    print(cov)
    for c in monde:
        s_=monde[c]; a,b=s_.first_valid_index(),s_.last_valid_index()
        inner=s_.loc[a:b]; 
        if inner.isna().any(): print('INTERNAL GAP',c,list(inner[inner.isna()].index))
    print(annuel['import_dependency']); print(annuel['import_dependency_flag'].notna().sum())
