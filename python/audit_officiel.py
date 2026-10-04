"""Taux d'inflation en moyenne annuelle publiés par la BCEAO, comparés à EDEN et FAOSTAT.
Chiffres relevés automatiquement dans les rapports PDF du site bceao.int le 04/10/2026
(rapport 2002-2011, tableau 1 ; rapport 2016, annexe 4). À recontrôler avant citation.
Le rapport 2017 (tableau 1) est ajouté dans audit_final.py."""
import pandas as pd
A = pd.read_pickle('all.pkl'); eden = A['eden']; fcp = A['fao_cp']; ISO = A['ISO']
off = {
 'BEN': {2002: 2.4, 2003: 1.5, 2004: 0.9, 2005: 5.4, 2006: 3.8, 2007: 1.3, 2008: 7.9, 2009: 0.4, 2010: 2.1, 2011: 2.7, 2014: -1.1, 2015: 0.3, 2016: -0.8},
 'BFA': {2002: 2.3, 2003: 2.0, 2004: -0.4, 2005: 6.4, 2006: 2.4, 2007: -0.3, 2008: 10.7, 2009: 0.9, 2010: -0.6, 2011: 2.8, 2014: -0.2, 2015: 0.9, 2016: -0.2},
 'CIV': {2002: 3.1, 2003: 3.3, 2004: 1.4, 2005: 3.9, 2006: 2.5, 2007: 1.9, 2008: 6.3, 2009: 0.5, 2010: 1.7, 2011: 4.9, 2014: 0.5, 2015: 1.2, 2016: 0.7},
 'GNB': {2002: 3.9, 2003: -3.5, 2004: 0.9, 2005: 3.4, 2006: 2.0, 2007: 4.6, 2008: 10.4, 2009: -2.8, 2010: 2.2, 2011: 5.1, 2014: -1.0, 2015: 1.5, 2016: 1.5},
 'MLI': {2002: 5.0, 2003: -1.3, 2004: -3.1, 2005: 6.4, 2006: 1.5, 2007: 1.4, 2008: 9.2, 2009: 2.4, 2010: 1.2, 2011: 3.0, 2014: 0.9, 2015: 1.4, 2016: -1.7},
 'NER': {2002: 2.6, 2003: -1.6, 2004: 0.2, 2005: 7.8, 2006: 0.0, 2007: 0.1, 2008: 11.3, 2009: 0.5, 2010: 0.9, 2011: 2.9, 2014: -0.9, 2015: 1.0, 2016: 0.2},
 'SEN': {2002: 2.3, 2003: 0.0, 2004: 0.5, 2005: 1.7, 2006: 2.1, 2007: 5.9, 2008: 5.8, 2009: -2.2, 2010: 1.2, 2011: 3.4, 2014: -1.1, 2015: 0.1, 2016: 0.8},
 'TGO': {2002: 3.1, 2003: -0.9, 2004: 0.4, 2005: 6.8, 2006: 2.2, 2007: 0.9, 2008: 8.7, 2009: 3.7, 2010: 1.5, 2011: 3.6, 2014: 0.2, 2015: 1.8, 2016: 0.9}}
O = pd.DataFrame(off)


def ann(D, suf):
    x = D.xs('cpi_all' + suf, axis=1, level=1)[ISO]; x.index = pd.PeriodIndex(x.index, freq='M')
    return 100 * x.groupby(x.index.year).mean().pct_change()


pd.to_pickle(dict(O=O, E=ann(eden, ''), F=ann(fcp, '_alt')), 'audit_official.pkl')
print('audit_official.pkl écrit :', O.shape)
