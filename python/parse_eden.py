import pandas as pd, numpy as np
MON={'JAN':1,'FEV':2,'MAR':3,'AVR':4,'MAI':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
NAME2ISO={"COTE D'IVOIRE":'CIV','BENIN':'BEN','BURKINA FASO':'BFA','MALI':'MLI','NIGER':'NER','SENEGAL':'SEN','GUINEE BISSAU':'GNB','TOGO':'TGO','ENSEMBLE UMOA':'UMOA'}
def parse(path):
    lines=[l.rstrip('\r') for l in open(path,encoding='utf-8').read().split('\n')]
    out=[]; i=0
    while i<len(lines):
        l=lines[i].strip()
        if l and not l.startswith('CODE;') and l.endswith(';') and l.count(';')==1:
            area=l[:-1]; hdr=lines[i+1].split(';')
            assert hdr[0]=='CODE'
            j=i+2
            while j<len(lines) and lines[j].strip():
                parts=lines[j].split(';')
                code,lib=parts[0],parts[1]
                for h,v in zip(hdr[2:],parts[2:]):
                    if not h: continue
                    m=MON[h[:3]]; y=int(h[3:])
                    v=v.strip()
                    val=np.nan if v in ('-','') else float(v.replace(',','.'))
                    out.append((NAME2ISO[area],code,lib,f'{y}-{m:02d}',val,v))
                j+=1
            i=j
        else: i+=1
    return pd.DataFrame(out,columns=['iso3','code','libelle','date','value','raw'])
if __name__=='__main__':
    d=pd.concat([parse('exportIndicateurs.csv'),parse('exportIndicateurs_1.csv')],ignore_index=True)
    print(d.groupby(['iso3','code','libelle']).value.count())
    d['var']=d.libelle.map({'Indice des prix a la consommation':'cpi_all','Indice des prix de la fonction alimentation':'cpi_food'})
    d['year']=d.date.str[:4]
    print(d.groupby(['iso3','var','year']).value.mean().unstack('year')[['2008','2014','2015','2023','2024','2025']].round(2))
    # unusual raw strings (non 3-decimal, zeros)
    print(d[(d.value==0)])
    print(d[d.raw.str.contains(r'[^0-9,\-]')])
    # internal gaps
    for (iso,var),g in d.groupby(['iso3','var']):
        g=g.sort_values('date'); nn=g[g.value.notna()]
        inner=g[(g.date>=nn.date.min())&(g.date<=nn.date.max())]
        print(iso,var,'first',nn.date.min(),'last',nn.date.max(),'internal gaps',inner.value.isna().sum(), list(inner[inner.value.isna()].date)[:20])
    d.to_pickle('eden.pkl')
