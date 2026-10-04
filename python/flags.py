import pandas as pd, numpy as np
A=pd.read_pickle('all.pkl'); eden=A['eden']; fcp=A['fao_cp']; ffl=A['fao_fl']; M=A['MONTHS']; ISO=A['ISO']; monde=A['monde']
b=pd.read_pickle('bull_ihpc.pkl')
THR_DIV=2.0   # points de % (variation mensuelle en log x100)
THR_Z=4.0
def mm(s): return 100*np.log(s).diff()
def rz(x):
    x=x.dropna(); med=x.median(); mad=(x-med).abs().median()*1.4826
    return (x-med)/mad
flag={iso:pd.Series('',index=M) for iso in ISO}; note={iso:pd.Series('',index=M) for iso in ISO}
anom=[]
def add(iso,d,tok,txt):
    if d not in flag[iso].index: return
    cur=flag[iso][d]
    if tok and tok not in cur.split(';'): flag[iso][d]=(cur+';'+tok).strip(';')
    if txt: note[iso][d]=(note[iso][d]+' | '+txt).strip(' |')
for iso in ISO:
    # FAOSTAT flags
    fa=ffl[(iso,'cpi_all_alt')].reindex(M); ff=ffl[(iso,'cpi_food_alt')].reindex(M)
    for d in M:
        if pd.notna(fa[d]) or pd.notna(ff[d]): flag[iso][d]=f"{fa[d] if pd.notna(fa[d]) else '-'}|{ff[d] if pd.notna(ff[d]) else '-'}"
    for v,tok in [('cpi_all','DIV_ALL'),('cpi_food','DIV_FOOD')]:
        e=eden[(iso,v)]; f=fcp[(iso,v+'_alt')]
        de=mm(e).reindex(M); df=mm(f).reindex(M); z=rz(mm(e).loc['1999-02':]).reindex(M)
        for d in M:
            div=abs(de[d]-df[d]) if pd.notna(de[d]) and pd.notna(df[d]) else np.nan
            isdiv=pd.notna(div) and div>THR_DIV; isz=pd.notna(z[d]) and abs(z[d])>THR_Z
            if isdiv: add(iso,d,tok,f"{v} : variation mensuelle EDEN {de[d]:+.1f} % contre FAOSTAT {df[d]:+.1f} %")
            if isdiv or isz:
                anom.append(dict(iso3=iso,variable=v,date=d,mm_eden=round(de[d],2),mm_faostat=round(df[d],2) if pd.notna(df[d]) else None,ecart=round(div,2) if pd.notna(div) else None,z=round(z[d],1) if pd.notna(z[d]) else None,crit=('divergence' if isdiv else '')+(' + ' if isdiv and isz else '')+('extrême' if isz else '')))
# GNB retropolation
for d in M:
    if d<'2002-07': add('GNB',d,'EDEN_RETRO','cpi_all EDEN proportionnel à la Côte d\'Ivoire (ratio 0,958 à 0,960) : rétropolation probable ; cpi_food absent d\'EDEN ; cpi_food_alt imputé par FAOSTAT (flag I)')
add('GNB','2002-07','EDEN_RUPTURE','Début de la série propre à la Guinée-Bissau dans EDEN : cpi_all passe de 58,7 à 66,7 (+13,6 %), première observation de cpi_food')
# plateaux EDEN (valeur identique >= 4 mois consécutifs)
for iso in ISO:
    for v in ['cpi_all','cpi_food']:
        e=eden[(iso,v)].reindex(M).dropna(); run=[]
        vals=list(e.items())
        i=0
        while i<len(vals):
            j=i
            while j+1<len(vals) and vals[j+1][1]==vals[i][1]: j+=1
            if j-i+1>=4:
                for k in range(i+1,j+1):
                    add(iso,vals[k][0],'EDEN_PLATEAU',f"{v} : valeur EDEN identique pendant {j-i+1} mois ({vals[i][0]} à {vals[j][0]})")
                anom.append(dict(iso3=iso,variable=v,date=vals[i][0],mm_eden=0.0,mm_faostat=None,ecart=None,z=None,crit=f'plateau de {j-i+1} mois (jusqu\'à {vals[j][0]})'))
            i=j+1
# bulletin differences
for _,r in b[b.iso3.isin(ISO)].iterrows():
    if abs(r.d_all)>0.15 or abs(r.d_food)>0.15:
        add(r.iso3,r.date,'BULL_DIFF',f"Bulletin BCEAO T1 2026 : IHPC global {r.ihpc_global:.1f}, division 1 {r.ihpc_div1:.1f} (EDEN : {r.eden_all:.1f} et {r.eden_food:.1f})".replace('.',','))
for iso in ISO:
    add(iso,'2025-01','', "Premier mois de l'IHPC base 2023 (nouvelle nomenclature à 13 divisions) : comparabilité avec 2024-12 non garantie")
    for d in ['2026-06','2026-07','2026-08','2026-09']: pass
AN=pd.DataFrame(anom)
def typ(r):
    if r.iso3=='GNB' and r.date=='2002-07': return 'Début de série (GNB)'
    if r.iso3=='GNB' and r.date<'2002-07': return 'Rétropolation EDEN (GNB)'
    if 'plateau' in r.crit: return 'Plateau EDEN (valeur répétée)'
    if r.date=='2008-01': return 'Changement de base probable (2008-01)'
    if r.date=='2017-01': return 'Changement de base probable (2017-01)'
    if r.date=='2025-01': return 'Passage à la base 2023 (2025-01)'
    if 'plateau' in r.crit: return 'Plateau EDEN (valeur répétée)'
    return 'Divergence EDEN / FAOSTAT' if 'divergence' in r.crit else 'Valeur extrême'
AN['type']=AN.apply(typ,axis=1)
pd.to_pickle(dict(flag=flag,note=note,anom=AN),'flags.pkl')
if __name__=='__main__':
    pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
    print(len(AN)); print(AN.crit.value_counts()); print(AN.type.value_counts()); print(AN.groupby(['iso3','variable']).size().unstack())
    print(AN.sort_values(['iso3','variable','date']).to_string())
    for iso in ISO: print(iso, flag[iso].value_counts().to_dict())
    # world outliers
    for c in monde.columns:
        if c in('gscpi','bceao_import_food'): continue
        z=rz(mm(monde[c])); o=z[z.abs()>THR_Z]
        if len(o): print(c,[(d,round(mm(monde[c])[d],1),round(v,1)) for d,v in o.items()])
