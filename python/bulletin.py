import re, pandas as pd, numpy as np
txt=open('bull.txt',encoding='utf-8').read().split('\n')
MF={'janv.':1,'févr.':2,'mars':3,'avr.':4,'mai':5,'juin':6,'juil.':7,'août':8,'sept.':9,'oct.':10,'nov.':11,'déc.':12}
N2I={'UEMOA':'UMOA','BENIN':'BEN','BURKINA':'BFA',"COTE D'IVOIRE":'CIV','GUINEE-BISSAU':'GNB','MALI':'MLI','NIGER':'NER','SENEGAL':'SEN','TOGO':'TGO'}
num=lambda s: float(s.replace(' ','').replace(' ','').replace(',','.'))
def monthly_rows(start,stop):
    """yield (date, [tokens]) for monthly lines between line indexes"""
    year=None
    for l in txt[start:stop]:
        m=re.match(r'\s*(20\d\d)?\s*(janv\.|févr\.|mars|avr\.|mai|juin|juil\.|août|sept\.|oct\.|nov\.|déc\.)\s+(.*)$',l)
        if not m: continue
        if m.group(1): year=int(m.group(1))
        yield f'{year}-{MF[m.group(2)]:02d}', m.group(3).split()
def ihpc():
    out=[]
    for i,l in enumerate(txt):
        m=re.match(r'Tableau 11\.1\.\d\.a Indice harmonisé des prix à la consommation – (.*)$',l.strip())
        if m:
            iso=N2I[m.group(1).strip()]
            j=next(k for k in range(i,len(txt)) if txt[k].startswith('Sources'))
            for date,tok in monthly_rows(i,j):
                out.append((iso,date,num(tok[0]),num(tok[1])))
    return pd.DataFrame(out,columns=['iso3','date','ihpc_global','ihpc_div1'])
def table(title, ncol_idx):
    i=next(k for k,l in enumerate(txt) if title in l)
    j=next(k for k in range(i,len(txt)) if 'Variation par rapport au trimestre' in txt[k])
    out={}
    for date,tok in monthly_rows(i,j):
        # join thousands separators: tokens like '1','849,13'
        vals=[]; k=0
        while k<len(tok):
            if re.fullmatch(r'\d{1,3}',tok[k]) and k+1<len(tok) and re.fullmatch(r'\d{3},\d+',tok[k+1]): vals.append(num(tok[k]+tok[k+1])); k+=2
            else: vals.append(num(tok[k])); k+=1
        out[date]=vals[ncol_idx]
    return pd.Series(out)
if __name__=='__main__':
    b=ihpc(); print(b.groupby('iso3').size()); print(b[b.iso3=='GNB'].head(8)); print(b[b.iso3=='TGO'].tail(3))
    usd=table('Tableau 9.3 Taux de change bilatéraux',0); print(usd)
    oil=table('Tableau 9.4 Cours mondiaux',5); print(oil)
    imp=table('Tableau 9.5 Produits alimentaires',5); print(imp)
