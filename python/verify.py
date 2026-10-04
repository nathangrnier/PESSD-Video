"""Vérification indépendante du fichier final contre les fichiers bruts (chemins de lecture distincts de extract.py)."""
import csv, random, re, math
import pandas as pd, numpy as np, openpyxl
FINAL='20261004_final_data_project_research_UEMOA_consolidated.xlsx'; ORIG='20261002_final_data_project_research_UEMOA.xlsx'
ISO=['BEN','BFA','CIV','GNB','MLI','NER','SEN','TGO']
wb=openpyxl.load_workbook(FINAL,data_only=True)
wf=openpyxl.load_workbook(FINAL)            # formules
wo=openpyxl.load_workbook(ORIG)
M=[f'{y}-{m:02d}' for y in range(2000,2027) for m in range(1,13)][:321]
assert M[-1]=='2026-09'
def col(ws,name,hrow=2):
    for c in range(1,ws.max_column+1):
        if ws.cell(hrow,c).value==name: return c
    raise KeyError(name)
def series(ws,name,n=321):
    c=col(ws,name); return [ws.cell(3+i,c).value for i in range(n)]
def same(a,b,tol=1e-9):
    if a in (None,'') and (b is None or (isinstance(b,float) and math.isnan(b))): return True
    if a in (None,'') or b is None or (isinstance(b,float) and math.isnan(b)): return False
    return abs(float(a)-float(b))<=tol*max(1,abs(float(b)))
bad=[]; nchk=0; pool=[]
def chk(tag,date,a,b,tol=1e-9):
    global nchk; nchk+=1
    if not same(a,b,tol): bad.append((tag,date,a,b))
    elif b is not None and not (isinstance(b,float) and math.isnan(b)): pool.append((tag,date,a,b))
# ---- structure
assert wb.sheetnames==wo.sheetnames==['Lisez-moi','Source','Monde','BEN','BFA','CIV','GNB','MLI','NER','SEN','TGO','Annuel','Pays','Data','Suivi','Controle','Parametres'], wb.sheetnames
for s in ['Monde']+ISO: assert [wb[s].cell(3+i,1).value for i in range(321)]==M, s
# ---- EDEN (lecture brute par position de colonne)
MON=['JAN','FEV','MAR','AVR','MAI','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
def eden_raw(path):
    out={}; area=None; hdr=None
    for row in csv.reader(open(path,encoding='utf-8'),delimiter=';'):
        if len(row)==2 and row[0] and row[0]!='CODE': area=row[0]
        elif row and row[0]=='CODE': hdr=row
        elif len(row)>10: out[(area,row[1])]=dict(zip(hdr[2:],row[2:]))
    return out
E=eden_raw('exportIndicateurs_1.csv'); E.update(eden_raw('exportIndicateurs.csv'))
AREA={'BEN':'BENIN','BFA':'BURKINA FASO','CIV':"COTE D'IVOIRE",'GNB':'GUINEE BISSAU','MLI':'MALI','NER':'NIGER','SEN':'SENEGAL','TGO':'TOGO'}
def eden_val(area,lib,d):
    v=E[(area,lib)][MON[int(d[5:])-1]+d[:4]]
    return None if v.strip()=='-' else float(v.replace(',','.'))
LIB={'cpi_all':'Indice des prix a la consommation','cpi_food':'Indice des prix de la fonction alimentation'}
for iso in ISO:
    for v in LIB:
        s=series(wb[iso],v)
        for d,x in zip(M,s): chk(f'{iso}.{v}',d,x,eden_val(AREA[iso],LIB[v],d))
for v,nm in [('cpi_all','cpi_all_umoa'),('cpi_food','cpi_food_umoa')]:
    for d,x in zip(M,series(wb['Monde'],nm)): chk(nm,d,x,eden_val('ENSEMBLE UMOA',LIB[v],d))
# ---- FAOSTAT CP
f=pd.read_csv('FAOSTAT_data_en_10-4-2026.csv')
MN=['January','February','March','April','May','June','July','August','September','October','November','December']
AR={'BEN':'Benin','BFA':'Burkina Faso','CIV':"Côte d'Ivoire",'GNB':'Guinea-Bissau','MLI':'Mali','NER':'Niger','SEN':'Senegal','TGO':'Togo'}
fk={(a,i,y,m):(v,fl) for a,i,y,m,v,fl in zip(f.Area,f.Item,f.Year,f.Months,f.Value,f.Flag)}
IT={'cpi_all_alt':'Consumer Prices, General Indices (2015 = 100)','cpi_food_alt':'Consumer Prices, Food Indices (2015 = 100)'}
for iso in ISO:
    qf=series(wb[iso],'quality_flag')
    for v in IT:
        s=series(wb[iso],v)
        for k,(d,x) in enumerate(zip(M,s)):
            t=fk.get((AR[iso],IT[v],int(d[:4]),MN[int(d[5:])-1]))
            chk(f'{iso}.{v}',d,x,t[0] if t else None)
            if t:
                part=qf[k].split(';')[0].split('|'); assert part[0 if v=='cpi_all_alt' else 1]==t[1],(iso,d,qf[k],t)
            else: assert qf[k] in (None,''),(iso,d,qf[k])
# ---- FAO FPI
p=pd.read_csv('food_price_indices_data.csv',header=2).dropna(how='all',axis=1); p=p[p.Date.notna()].set_index('Date')
for nm,c in [('fao_food','Food Price Index'),('fao_meat','Meat'),('fao_dairy','Dairy'),('fao_cereals','Cereals'),('fao_oils','Oils'),('fao_sugar','Sugar')]:
    for d,x in zip(M,series(wb['Monde'],nm)): chk(nm,d,x,float(p.loc[d,c]) if d in p.index else None)
# ---- Pink Sheet
k=pd.read_excel('CMO-Historical-Data-Monthly.xlsx',sheet_name='Monthly Prices',header=4)
k=k.rename(columns={k.columns[0]:'per'}); k=k[k.per.astype(str).str.match(r'^\d{4}M\d{2}$')].set_index('per')
for nm,c in [('oil_usd','Crude oil, Brent'),('rice_thai','Rice, Thai 5% '),('wheat_hrw','Wheat, US HRW'),('palm_oil','Palm oil'),('sugar_world','Sugar, world'),('maize','Maize')]:
    for d,x in zip(M,series(wb['Monde'],nm)): chk(nm,d,x,float(k.loc[d.replace('-','M'),c]))
# ---- ECB
ecb={r['DATE'][:7]:float(r[list(r)[2]]) for r in csv.DictReader(open('ECB_Data_Portal_20261004111939.csv',encoding='utf-8'))}
for d,x in zip(M,series(wb['Monde'],'eur_usd')): chk('eur_usd',d,x,ecb.get(d))
for d,x,e in zip(M,series(wb['Monde'],'usd_xof'),series(wb['Monde'],'eur_usd')): chk('usd_xof',d,x,655.957/e)
# ---- GSCPI
g=pd.read_excel('gscpi_data.xlsx',sheet_name='GSCPI Monthly Data',header=None,skiprows=5,usecols=[0,1]); g.columns=['d','v']; g=g.dropna()
gd={pd.to_datetime(a,format='%d-%b-%Y').strftime('%Y-%m'):float(b) for a,b in zip(g.d,g.v)}
for d,x in zip(M,series(wb['Monde'],'gscpi')): chk('gscpi',d,x,gd.get(d))
# ---- bceao_import_food : relecture du texte du PDF
from bulletin import table
t95=table('Tableau 9.5 Produits alimentaires',5)
for d,x in zip(M,series(wb['Monde'],'bceao_import_food')): chk('bceao_import_food',d,x,float(t95[d]) if d in t95.index else None)
# ---- import_food_idx recalcul indépendant
W={'rice_thai':30.5,'wheat_hrw':8.6,'fao_oils':8.3,'sugar_world':5.4,'fao_dairy':4.4}; tot=sum(W.values())
S={v:series(wb['Monde'],v) for v in W}
idx=[100*math.prod((S[v][i]/S[v][0])**(W[v]/tot) for v in W) for i in range(321)]
for d,x,y in zip(M,series(wb['Monde'],'import_food_idx'),idx): chk('import_food_idx',d,x,y,1e-9)
# ---- Annuel
wa=wb['Annuel']; yrs=[wa.cell(3+i,1).value for i in range(27)]; assert yrs==[str(y) for y in range(2000,2027)]
q=pd.read_csv('FAOSTAT_data_en_10-4-2026_2.csv'); q=q[(q.Item=='Cereals, primary')&(q.Element=='Production')]
qk={(a,y):(v,fl) for a,y,v,fl in zip(q.Area,q.Year,q.Value,q.Flag)}
s3=pd.read_csv('FAOSTAT_data_en_10-4-2026_1.csv'); sk={(a,int(y[:4])+1):(v,fl) for a,y,v,fl in zip(s3.Area,s3.Year,s3.Value,s3.Flag)}
w=pd.read_csv('API_TM.VAL.FOOD.ZS.UN_DS2_en_csv_v2_404666.csv',skiprows=4).set_index('Country Code')
for iso in ISO:
    for i,y in enumerate(range(2000,2027)):
        r=3+i
        t=qk.get((AR[iso],y)); chk(f'local_agri_supply_{iso}',y,wa.cell(r,col(wa,f'local_agri_supply_{iso}')).value,t[0] if t else None)
        assert wa.cell(r,col(wa,f'local_agri_supply_flag_{iso}')).value==(t[1] if t else None)
        t=sk.get((AR[iso],y)); chk(f'import_dependency_{iso}',y,wa.cell(r,col(wa,f'import_dependency_{iso}')).value,t[0] if t else None)
        assert wa.cell(r,col(wa,f'import_dependency_flag_{iso}')).value==(t[1] if t else None)
        v=w.loc[iso,str(y)] if str(y) in w.columns else None
        chk(f'food_imports_share_{iso}',y,wa.cell(r,col(wa,f'food_imports_share_{iso}')).value,None if v is None or pd.isna(v) else float(v))
        assert wa.cell(r,col(wa,f'gdp_real_{iso}')).value is None
print('contrôles valeur à valeur contre les sources :',nchk,'écarts :',len(bad)); print(bad[:10])
# ---- Data vs Monde / pays / Annuel / Pays
wd=wb['Data']; H={wd.cell(2,c).value:c for c in range(1,wd.max_column+1) if wd.cell(2,c).value}
wp=wb['Pays']; P={wp.cell(r,3).value:r for r in range(3,11)}; HP={wp.cell(2,c).value:c for c in range(2,17)}
MW=['fao_food','oil_usd','usd_xof','fao_cereals','fao_oils','fao_sugar','fao_dairy','fao_meat','rice_thai','wheat_hrw','palm_oil','sugar_world','maize','eur_usd','gscpi','bceao_import_food','import_food_idx']
CW=['cpi_all','cpi_food','cpi_all_alt','cpi_food_alt','rain_anom','quality_flag']
MS={v:series(wb['Monde'],v) for v in MW}
nd=0; errs=0; keys=set()
def eq(a,b):
    a=None if a=='' else a; b=None if b=='' else b
    if a is None or b is None: return a is None and b is None
    return a==b if isinstance(a,str) or isinstance(b,str) else abs(a-b)<1e-12*max(1,abs(b))
for bi,iso in enumerate(ISO):
    CS={v:series(wb[iso],v) for v in CW}
    for i,d in enumerate(M):
        r=3+bi*321+i
        assert wd.cell(r,H['Date']).value==d and wd.cell(r,H['iso3']).value==iso, (r,iso,d)
        assert wd.cell(r,H['country']).value==wp.cell(P[iso],2).value
        keys.add((iso,d))
        for v in MW: nd+=1; errs+=not eq(wd.cell(r,H[v]).value,MS[v][i])
        for v in CW: nd+=1; errs+=not eq(wd.cell(r,H[v]).value,CS[v][i])
        y=int(d[:4])-2000
        for v in ['local_agri_supply','import_dependency','food_imports_share','gdp_real']:
            nd+=1; errs+=not eq(wd.cell(r,H[v]).value,wa.cell(3+y,col(wa,f'{v}_{iso}')).value)
        for v in ['coastal','food_weight','import_share_cpi']:
            nd+=1; errs+=not eq(wd.cell(r,H[v]).value,wp.cell(P[iso],HP[v]).value)
        nd+=1; errs+=wd.cell(r,H['ihpc_base']).value!=('base 2023' if d>='2025-01' else 'avant 2025')
assert len(keys)==2568 and wd.max_row==2570
print('Data : cellules comparées',nd,'écarts',errs,'clés uniques',len(keys))
# ---- erreurs de formule, toutes feuilles
ne=0
for ws in wb:
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value,str) and re.match(r'^#(REF!|VALUE!|N/A|DIV/0!|NAME\?|NUM!|NULL!)',c.value): ne+=1; print('ERR',ws.title,c.coordinate,c.value)
print('cellules en erreur :',ne)
# ---- formules d'origine conservées (fichier avant recalcul = sortie openpyxl)
wpre=openpyxl.load_workbook('pre_recalc.xlsx'); nf=0; lost=[]
for ws in wo:
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value,str) and c.value.startswith('='):
                nf+=1
                if wpre[ws.title][c.coordinate].value!=c.value: lost.append((ws.title,c.coordinate))
print("formules d'origine :",nf,'modifiées ou perdues :',len(lost),lost[:5])
# valeurs d'origine conservées (Pays, Parametres, Controle haut)
chg=[]
for name in ['Pays','Parametres','Controle']:
    for row in wo[name].iter_rows():
        for c in row:
            if c.value is not None and not (isinstance(c.value,str) and c.value.startswith('=')):
                if wb[name][c.coordinate].value!=c.value: chg.append((name,c.coordinate,c.value,wb[name][c.coordinate].value))
print("valeurs d'origine modifiées dans Pays / Parametres / Controle :",chg)
# ---- tirage aléatoire
random.seed(20261004)
print('\nTirage aléatoire de 80 observations (classeur = source) :')
for tag,d,a,b in sorted(random.sample(pool,80)): print(f'  {tag:28s} {d}  classeur={a!r:22}  source={b!r}')
assert not bad and errs==0 and ne==0 and not lost and not chg
print('\nTOUT EST CONFORME')
