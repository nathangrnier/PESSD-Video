import pandas as pd, numpy as np
pd.set_option('display.width',280); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',600)
A=pd.read_pickle('all.pkl'); eden=A['eden']; fcp=A['fao_cp']; M=A['MONTHS']; ISO=A['ISO']
P=pd.period_range('2000-01','2026-09',freq='M')
def S(iso,v):
    e=eden[(iso,v)].reindex(M); f=fcp[(iso,v+'_alt')].reindex(M); return e,f
def windows(iso,v,thr=0.3,maxgap=6):
    e,f=S(iso,v); r=100*(np.log(f)-np.log(e)); dr=r.diff()
    idx=[i for i,d in enumerate(M) if pd.notna(dr[d]) and abs(dr[d])>thr]
    out=[]; 
    if not idx: return out,r
    s=p=idx[0]
    for i in idx[1:]:
        if i-p>maxgap: out.append((s,p)); s=i
        p=i
    out.append((s,p)); return out,r
rows=[]
for iso in ISO:
    for v in ['cpi_all','cpi_food']:
        e,f=S(iso,v); w,r=windows(iso,v)
        me=100*np.log(e).diff(); mf=100*np.log(f).diff()
        ye=100*(e/e.shift(12)-1); yf=100*(f/f.shift(12)-1)
        for (a,b) in w:
            if b-a<2 and abs(r.iloc[min(b+1,len(r)-1)]-r.iloc[max(a-1,0)])<0.3: continue   # écarts ponctuels d'arrondi
            pre=r.iloc[max(a-6,0):a].mean(); post=r.iloc[b+1:b+7].mean()
            first=M[a]
            rows.append(dict(iso=iso,var=v,debut=M[a],fin=M[b],mois=b-a+1,
                 mm_eden_debut=round(me.iloc[a],2),mm_fao_debut=round(mf.iloc[a],2),
                 saut_niveau_net=round(pre-post,2) if pd.notna(post) and pd.notna(pre) else None,   # >0 : EDEN a plus augmenté que FAOSTAT sur la fenêtre
                 ecart_max=round((r.iloc[a:b+1]-pre).abs().max(),2) if pd.notna(pre) else None,
                 corr_mm=round(np.corrcoef(me.iloc[a:b+1],mf.iloc[a:b+1])[0,1],2) if b-a>3 else None,
                 sd_mm_eden=round(me.iloc[a:b+1].std(),2),sd_mm_fao=round(mf.iloc[a:b+1].std(),2)))
W=pd.DataFrame(rows); print(W.to_string()); W.to_pickle('audit_windows.pkl')
# 2008 : profil du glissement annuel
print('\n2008 : glissement annuel déc.2007 -> janv.2008, écart-type du glissement sur 2008, pic')
r2=[]
for iso in ISO:
    for v in ['cpi_all','cpi_food']:
        e,f=S(iso,v); ye=100*(e/e.shift(12)-1); yf=100*(f/f.shift(12)-1)
        me=100*(e/e.shift(1)-1); mf=100*(f/f.shift(1)-1)
        # corrélation du profil mensuel 2008 avec celui de 2007 (fév-déc)
        m8=[f'2008-{m:02d}' for m in range(2,13)]; m7=[f'2007-{m:02d}' for m in range(2,13)]
        r2.append(dict(iso=iso,var=v,yy_e_0712=ye['2007-12'],yy_e_0801=ye['2008-01'],yy_f_0712=yf['2007-12'],yy_f_0801=yf['2008-01'],
            sd_yy08_e=ye.loc['2008-01':'2008-12'].std(),sd_yy08_f=yf.loc['2008-01':'2008-12'].std(),
            pic_e=ye.loc['2008-01':'2008-12'].idxmax(),pic_f=yf.loc['2008-01':'2008-12'].idxmax(),
            max_e=ye.loc['2008-01':'2008-12'].max(),max_f=yf.loc['2008-01':'2008-12'].max(),
            moy08_e=100*(e.loc['2008-01':'2008-12'].mean()/e.loc['2007-01':'2007-12'].mean()-1),moy08_f=100*(f.loc['2008-01':'2008-12'].mean()/f.loc['2007-01':'2007-12'].mean()-1),
            corr_e_0807=np.corrcoef(me[m8],me[m7])[0,1],corr_f_0807=np.corrcoef(mf[m8],mf[m7])[0,1],
            cum_e=100*(e['2009-12']/e['2007-12']-1),cum_f=100*(f['2009-12']/f['2007-12']-1)))
R2=pd.DataFrame(r2); print(R2.round(2).to_string()); R2.to_pickle('audit_2008.pkl')
