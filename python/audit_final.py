"""Audit EDEN / FAOSTAT aux changements de base : tables finales (classeur + page)."""
import pandas as pd, numpy as np, json
A=pd.read_pickle('all.pkl'); eden=A['eden']; fcp=A['fao_cp']; M=A['MONTHS']; ISO=A['ISO']
W=pd.read_pickle('audit_windows.pkl'); OFF=pd.read_pickle('audit_official.pkl')['O']
OFF.loc[2017]=pd.Series({'BEN':0.1,'BFA':0.4,'CIV':0.7,'GNB':1.0,'MLI':1.8,'NER':2.4,'SEN':1.3,'TGO':-0.8})   # BCEAO, rapport 2017, tableau 1
OFF=OFF.sort_index()
FW={'BEN':37.5,'BFA':50.2,'CIV':29.3,'GNB':60.3,'MLI':58.5,'NER':47.8,'SEN':49.6,'TGO':32.9}
mm=lambda s,d: 100*(s[d]/s[M[M.index(d)-1]]-1)
# ---- fenêtres retenues + traitement proposé
PATCH={('CIV','cpi_all','2008-01'):'2009-11',('MLI','cpi_all','2008-01'):'2009-07',('NER','cpi_all','2008-01'):'2009-04',
       ('GNB','cpi_all','2008-01'):'2010-03',('SEN','cpi_all','2007-08'):'2010-01',('CIV','cpi_food','2008-01'):'2010-04'}
rows=[]
for r in W.itertuples():
    if r.debut>'2024-12': continue
    if not (r.mois>=3 or (r.saut_niveau_net is not None and abs(r.saut_niveau_net)>=1)): continue
    key=(r.iso,r.var,r.debut)
    if key in PATCH: t='FAOSTAT dans la fenêtre'
    elif r.iso=='GNB' and r.var=='cpi_all' and r.debut=='2000-02': t='Exclure (rétropolation EDEN avant 2002-07)'
    else: t='EDEN'
    rows.append(dict(iso3=r.iso,variable=r.var,debut=r.debut,fin=r.fin,mois=int(r.mois),mm_eden=r.mm_eden_debut,mm_fao=r.mm_fao_debut,net=r.saut_niveau_net,corr=r.corr_mm,traitement=t))
WIN=pd.DataFrame(rows)
# SEN cpi_all : deux fenêtres contiguës 2007-08→2009-01 et 2009-09→2010-01 regroupées dans le traitement
WIN.loc[(WIN.iso3=='SEN')&(WIN.variable=='cpi_all')&(WIN.debut=='2009-09'),'traitement']='FAOSTAT dans la fenêtre'
# ---- janvier 2008
J=[]
for iso in ISO:
    ea,fa,ef,ff=[mm(eden[(iso,'cpi_all')],'2008-01'),mm(fcp[(iso,'cpi_all_alt')],'2008-01'),mm(eden[(iso,'cpi_food')],'2008-01'),mm(fcp[(iso,'cpi_food_alt')],'2008-01')]
    w=FW[iso]/100
    nf_rt=(fa-w*ef)/(1-w); nf_ed=(ea-w*ef)/(1-w)
    if iso in('CIV',): lec='Saut de raccord dans EDEN (indice global et alimentation) ; FAOSTAT sans saut'
    elif iso in('MLI','NER'): lec='Saut de raccord dans EDEN (indice global). Alimentation : même saut dans les deux sources, incompatible avec l\'indice global publié en temps réel'
    elif iso in('BFA','BEN'): lec='Hausse en partie réelle : l\'indice global en temps réel monte aussi. Alimentation identique dans les deux sources'
    else: lec='Pas de saut en janvier 2008'
    J.append(dict(iso3=iso,all_eden=ea,all_fao=fa,food_eden=ef,food_fao=ff,poids=FW[iso],nonfood_rt=nf_rt,lecture=lec))
JAN=pd.DataFrame(J)
# ---- inflation annuelle
def ann(D,suf):
    x=D.xs('cpi_all'+suf,axis=1,level=1)[ISO].copy(); x.index=pd.PeriodIndex(x.index,freq='M'); a=x.groupby(x.index.year).mean(); return 100*a.pct_change()
E=ann(eden,''); F=ann(fcp,'_alt')
ANN=[dict(iso3=i,annee=int(y),bceao=float(OFF.loc[y,i]),eden=float(E.loc[y,i]),fao=float(F.loc[y,i])) for i in ISO for y in OFF.index]
ANN=pd.DataFrame(ANN)
print(WIN.to_string()); print(JAN.round(2).to_string())
d=ANN.assign(de=(ANN.eden-ANN.bceao).abs(),df=(ANN.fao-ANN.bceao).abs())
print('n',len(d),'EDEN à 0,15 près',(d.de<=0.15).sum(),'FAOSTAT',(d.df<=0.15).sum())
print(d[(d.de>0.15)|(d.df>0.15)].round(1).to_string())
# pic 2008
for iso in ISO:
    e=eden[(iso,'cpi_all')]; f=fcp[(iso,'cpi_all_alt')]; ye=100*(e/e.shift(12)-1); yf=100*(f/f.shift(12)-1)
    print(iso,'yy janv.08 E/F',round(ye['2008-01'],1),round(yf['2008-01'],1),'pic 2008 E',ye.loc['2008-01':'2008-12'].idxmax(),round(ye.loc['2008-01':'2008-12'].max(),1),'F',yf.loc['2008-01':'2008-12'].idxmax(),round(yf.loc['2008-01':'2008-12'].max(),1))
u=eden[('UMOA','cpi_all')]; print('UMOA EDEN août 2008',round(100*(u['2008-08']/u['2007-08']-1),1))
pd.to_pickle(dict(WIN=WIN,JAN=JAN,ANN=ANN,OFF=OFF,PATCH=PATCH),'audit_final.pkl')
# ---- données pour la page
MS=[m for m in M if '2006-01'<=m<='2019-12']
data=dict(months=MS,iso=ISO,series={f'{i}|{v}|{s}':[None if pd.isna(x) else round(float(x),3) for x in (eden[(i,v)] if s=='eden' else fcp[(i,v+'_alt')]).reindex(MS)] for i in ISO for v in ['cpi_all','cpi_food'] for s in ['eden','fao']},
          win=WIN.replace({np.nan:None}).to_dict('records'),jan=JAN.round(2).to_dict('records'),ann=ANN.round(2).to_dict('records'))
json.dump(data,open('audit_data.json','w'),ensure_ascii=False)
import os; print(os.path.getsize('audit_data.json'))
