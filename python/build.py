"""Consolidation du classeur UEMOA : remplit le fichier cible à partir des sources.
Lit l'original (jamais modifié) et écrit le fichier consolidé."""
import re, shutil
from copy import copy
import numpy as np, pandas as pd, openpyxl
from openpyxl.utils import get_column_letter as L
from bulletin import ihpc, table, txt as BTXT

SRC = '20261002_final_data_project_research_UEMOA.xlsx'
OUT = '20261004_final_data_project_research_UEMOA_consolidated.xlsx'
TODAY = '04/10/2026'

A = pd.read_pickle('all.pkl'); F = pd.read_pickle('flags.pkl')
eden, fcp, ffl, monde, annuel = A['eden'], A['fao_cp'], A['fao_fl'], A['monde'], A['annuel']
M, ISO, YEARS = A['MONTHS'], A['ISO'], A['YEARS']
flag, note, AN = F['flag'], F['note'], F['anom']
NAMES = {'BEN': 'Bénin', 'BFA': 'Burkina Faso', 'CIV': "Côte d'Ivoire", 'GNB': 'Guinée-Bissau', 'MLI': 'Mali',
         'NER': 'Niger', 'SEN': 'Sénégal', 'TGO': 'Togo'}
ROW = {d: 3 + i for i, d in enumerate(M)}          # ligne d'un mois dans Monde / onglets pays
fr = lambda x, n=1: f'{x:.{n}f}'.replace('.', ',')

wb = openpyxl.load_workbook(SRC)

# ------------------------------------------------------------------ styles de référence (repris du classeur)
S_HEAD = wb['Monde']['A2']            # en-tête
S_LAB_B = wb['Lisez-moi']['B3']       # libellé gras, fond blanc
S_LAB = wb['Lisez-moi']['C3']         # texte, fond blanc
S_PRE = wb['Controle']['C3']          # valeur pré-remplie (gris clair)
S_FORM = wb['Controle']['D3']         # formule (turquoise clair)
S_PASTE = wb['Monde']['B3']           # cellule de collecte (blanc)


def sty(c, ref, nf=None):
    c.font = copy(ref.font); c.fill = copy(ref.fill); c.border = copy(ref.border)
    c.alignment = copy(ref.alignment); c.number_format = nf if nf else ref.number_format
    return c


def put(ws, addr, val, ref=None, nf=None):
    c = ws[addr]; c.value = val
    if ref is not None: sty(c, ref, nf)
    elif nf: c.number_format = nf
    return c


def num(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) or pd.isna(v) else float(v)



def set_width(ws, letter, width):
    """Fixe la largeur d'une seule colonne en scindant, au besoin, le groupe de colonnes qui la contient."""
    from openpyxl.utils import column_index_from_string as CI
    from openpyxl.worksheet.dimensions import ColumnDimension
    idx = CI(letter)
    for key, dim in list(ws.column_dimensions.items()):
        lo, hi = (dim.min or CI(key)), (dim.max or CI(key))
        if lo <= idx <= hi and not (lo == hi == idx):
            w = dim.width; del ws.column_dimensions[key]
            for a, b_ in [(lo, idx - 1), (idx + 1, hi)]:
                if a <= b_:
                    ws.column_dimensions[L(a)] = ColumnDimension(ws, index=L(a), min=a, max=b_, width=w, customWidth=True)
    ws.column_dimensions[letter] = ColumnDimension(ws, index=letter, min=idx, max=idx, width=width, customWidth=True)


def hdr_map(ws, row=2):
    return {ws.cell(row, c).value: c for c in range(1, ws.max_column + 1) if ws.cell(row, c).value}


# ================================================================== 1. MONDE
ws = wb['Monde']
put(ws, 'S2', 'cpi_all_umoa', S_HEAD); put(ws, 'T2', 'cpi_food_umoa', S_HEAD)
set_width(ws, 'S', 13); set_width(ws, 'T', 14)
H = hdr_map(ws)
assert [ws.cell(r, 1).value for r in range(3, 324)] == M
for var in ['fao_food', 'fao_cereals', 'fao_oils', 'fao_sugar', 'fao_dairy', 'fao_meat', 'oil_usd', 'rice_thai',
            'wheat_hrw', 'palm_oil', 'sugar_world', 'maize', 'eur_usd', 'gscpi', 'bceao_import_food',
            'cpi_all_umoa', 'cpi_food_umoa']:
    col = H[var]
    for d in M:
        c = ws.cell(ROW[d], col)
        assert not (isinstance(c.value, str) and c.value.startswith('=')), (var, d)
        c.value = num(monde.loc[d, var])
# usd_xof (O) et import_food_idx (R) : formules existantes conservées telles quelles

# ================================================================== 2. ONGLETS PAYS
for iso in ISO:
    ws = wb[iso]; H = hdr_map(ws)
    assert [ws.cell(r, 1).value for r in range(3, 324)] == M
    for d in M:
        r = ROW[d]
        ws.cell(r, H['cpi_all']).value = num(eden.loc[d, (iso, 'cpi_all')])
        ws.cell(r, H['cpi_food']).value = num(eden.loc[d, (iso, 'cpi_food')])
        ws.cell(r, H['cpi_all_alt']).value = num(fcp[(iso, 'cpi_all_alt')].get(d, np.nan))
        ws.cell(r, H['cpi_food_alt']).value = num(fcp[(iso, 'cpi_food_alt')].get(d, np.nan))
        ws.cell(r, H['quality_flag']).value = flag[iso][d] or None
        ws.cell(r, H['note']).value = note[iso][d] or None
    set_width(ws, L(H['quality_flag']), 30); set_width(ws, L(H['note']), 110)

# ================================================================== 3. ANNUEL
ws = wb['Annuel']
assert [ws.cell(r, 1).value for r in range(3, 30)] == [str(y) for y in YEARS]
c0 = ws.max_column + 1                                   # première colonne libre (AH)
for k, iso in enumerate(ISO):
    put(ws, f'{L(c0 + k)}2', f'local_agri_supply_flag_{iso}', S_HEAD)
    put(ws, f'{L(c0 + 8 + k)}2', f'import_dependency_flag_{iso}', S_HEAD)
    set_width(ws, L(c0 + k), 27); set_width(ws, L(c0 + 8 + k), 27)
H = hdr_map(ws)
for iso in ISO:
    for i, y in enumerate(YEARS):
        r = 3 + i
        ws.cell(r, H[f'local_agri_supply_{iso}']).value = num(annuel['local_agri_supply'].loc[y, iso])
        ws.cell(r, H[f'import_dependency_{iso}']).value = num(annuel['import_dependency'].loc[y, iso])
        ws.cell(r, H[f'food_imports_share_{iso}']).value = num(annuel['food_imports_share'].loc[y, iso])
        v = annuel['local_agri_supply_flag'].loc[y, iso]; ws.cell(r, H[f'local_agri_supply_flag_{iso}']).value = None if pd.isna(v) else v
        v = annuel['import_dependency_flag'].loc[y, iso]; ws.cell(r, H[f'import_dependency_flag_{iso}']).value = None if pd.isna(v) else v
# notes sous le tableau
for k, t in enumerate([
    "local_agri_supply : FAOSTAT QCL, « Cereals, primary », élément Production, en tonnes. Flags : A = valeur officielle, E = valeur estimée (colonnes local_agri_supply_flag_*).",
    "import_dependency : FAOSTAT FS, « Cereal import dependency ratio (percent) (3-year average) ». La moyenne triennale est affectée à son année centrale (2000-2002 en 2001). Toutes les valeurs portent le flag E (estimation FAO). Aucune extrapolation : les années sans donnée restent vides.",
    "food_imports_share : Banque mondiale, WDI, TM.VAL.FOOD.ZS.UN, en % des importations de marchandises. Années manquantes laissées vides, sans interpolation.",
    "gdp_real : aucun fichier fourni lors de la consolidation du 04/10/2026 ; colonnes laissées vides.",
    "Dans l'onglet Data, la valeur annuelle est répétée sur les 12 mois de l'année, sans interpolation entre années."]):
    put(ws, f'A{32 + k}', t, S_LAB)

# ================================================================== 4. diagnostics chiffrés (pour les textes)
b = ihpc()
b['eden_all'] = [eden.loc[d, (i, 'cpi_all')] for i, d in zip(b.iso3, b.date)]
b['eden_food'] = [eden.loc[d, (i, 'cpi_food')] for i, d in zip(b.iso3, b.date)]
b['d_all'] = (b.eden_all - b.ihpc_global).round(2); b['d_food'] = (b.eden_food - b.ihpc_div1).round(2)
bc = b[b.iso3 != 'UMOA']
n_cmp = len(bc); n_diff = int(((bc.d_all.abs() > 0.051) | (bc.d_food.abs() > 0.051)).sum())
bull_usd = table('Tableau 9.3 Taux de change bilatéraux', 0)
bull_oil = table('Tableau 9.4 Cours mondiaux', 5)
usd_calc = 655.957 / monde.eur_usd
usd_maxdiff = float((100 * (usd_calc.reindex(bull_usd.index) / bull_usd - 1)).abs().max())


def pct(iso, var, d):
    s = eden[(iso, var)]; i = s.index.get_loc(d); return 100 * (s.iloc[i] / s.iloc[i - 1] - 1)


jan = {}
for iso in ISO:
    for var in ['cpi_all', 'cpi_food']:
        s = eden[(iso, var)]; p = 100 * (s / s.shift(1) - 1)
        js = p[[f'{y}-01' for y in range(2001, 2025)]].dropna()
        jan[(iso, var)] = (float(p['2025-01']), float(js.mean()), float(js.std()))
n_div = int(AN.crit.str.contains('divergence').sum()); n_ext = int(AN.crit.str.contains('extrême').sum())
AN = AN[AN.date >= '2000-02'].copy()

# ================================================================== 5. SOURCE
ws = wb['Source']
R = {ws.cell(r, 2).value: r for r in range(3, 35)}
COLS = dict(F='F', G='G', J='J', K='K', L='L', M='M', N='N', O='O', P='P', Q='Q')


def src(name, **kw):
    r = R[name]
    for k, v in kw.items():
        c = ws[f'{k}{r}']; c.value = v
        if k == 'L':
            c.hyperlink = v if v else None


EDEN_URL = 'https://edenpub.bceao.int/'
FPI_FILE = 'food_price_indices_data.csv (indices nominaux mensuels, 1990-01 à 2026-09)'
PINK = 'CMO-Historical-Data-Monthly.xlsx (mise à jour du 02/10/2026), feuille Monthly Prices'
LU = f'Fichier lu le {TODAY}'
src('cpi_all', F='BCEAO, base de données EDEN (origine : instituts nationaux de statistique)',
    G='Indice, base 100 = 2023', J='Collé',
    K='exportIndicateurs_1.csv, ligne « Indice des prix a la consommation » (codes xxxSR3017M0BP), 8 pays, 1999-01 à 2026-05',
    L=EDEN_URL, M='cpi_all_alt (FAOSTAT) ; FMI, CPI ; Banque mondiale',
    O=f'{LU} ; recoupé avec le Bulletin trimestriel BCEAO T1 2026, tableaux 11.1.x.a', P='Vérifié',
    Q="Série principale. EDEN publie tout l'historique en base 100 = 2023 (moyenne 2023 = 100,0 dans les 8 pays) : pas de saut d'échelle, mais des sauts mensuels aux dates de changement de base (2008-01, 2017-01, 2025-01) et, pour la Guinée-Bissau, une rétropolation avant 2002-07. Aucun raccord fait ici : voir quality_flag et l'onglet Controle. Mois 1999 hors gabarit.")
src('cpi_food', F='BCEAO, base de données EDEN (origine : instituts nationaux de statistique)',
    G='Indice, base 100 = 2023', J='Collé',
    K='exportIndicateurs_1.csv, ligne « Indice des prix de la fonction alimentation » (codes xxxSR3021M0BP), 8 pays, 1999-01 à 2026-05 (Guinée-Bissau : à partir de 2002-07)',
    L=EDEN_URL, M='cpi_food_alt (FAOSTAT) ; FMI, CPI détaillé',
    O=f'{LU} ; recoupé avec la division 1 des tableaux 11.1.x.a du Bulletin trimestriel BCEAO T1 2026', P='Vérifié',
    Q="Mêmes limites que cpi_all. Indice en niveau. Guinée-Bissau : 30 mois manquants (2000-01 à 2002-06), non comblés. Fonction alimentation = division 1 de l'IHPC (produits alimentaires et boissons non alcoolisées).")
src('fao_food', J='Collé', K=f'{FPI_FILE}, colonne Food Price Index', O=LU, P='Collecté',
    Q='Indice nominal en dollars. Dernier point du fichier : septembre 2026.')
for nm, col in [('fao_cereals', 'Cereals'), ('fao_oils', 'Oils'), ('fao_sugar', 'Sugar'), ('fao_dairy', 'Dairy'), ('fao_meat', 'Meat')]:
    src(nm, J='Collé', K=f'{FPI_FILE}, colonne {col}', O=LU, P='Collecté')
for nm, lab, unit in [('oil_usd', 'Crude oil, Brent', '$/bbl'), ('rice_thai', 'Rice, Thai 5%', '$/mt'), ('wheat_hrw', 'Wheat, US HRW', '$/mt'),
                      ('palm_oil', 'Palm oil', '$/mt'), ('sugar_world', 'Sugar, world', '$/kg'), ('maize', 'Maize', '$/mt')]:
    src(nm, J='Collé', K=f'{PINK}, colonne « {lab} » ({unit}), 2000-01 à 2026-09', O=f'{LU} (contenu vérifié)', P='Collecté')
src('palm_oil', Q="Unité d'origine conservée. Selon la feuille Description du fichier, la définition de la série change : Malaisie 5 % CIF Europe jusqu'à 2001-11, RBD CIF Rotterdam de 2001-12 à 2020-12, RBD FOB Malaisie de 2021-01 à 2024-10, 5 % vrac CIF Europe de 2024-11 à 2025-01, huile brute DAP de 2025-02 à 2025-12, RBD FOB depuis 2026-01.")
src('sugar_world', Q="Unité d'origine conservée : dollars par kilogramme (les autres produits agricoles sont en dollars par tonne).")
src('oil_usd', Q="Garder le Brent sur toute la période. Le bulletin BCEAO publie un cours du pétrole différent (tableau 9.4, cotation de New York), non comparable terme à terme. La feuille « Mismatch Details » du fichier ne concerne aucune des six séries retenues.")
src('usd_xof', O=f"Calcul ; recoupé avec le tableau 9.3 du Bulletin trimestriel BCEAO T1 2026 (écart maximal {fr(usd_maxdiff, 4)} % sur 18 mois)",
    Q="usd_xof = 655,957 / eur_usd (parité fixe : 1 EUR = 655,957 FCFA, onglet Parametres). Formule conservée dans l'onglet Monde.")
src('eur_usd', J='Collé', K='ECB_Data_Portal_20261004111939.csv, série EXR.M.USD.EUR.SP00.A, 1999-01 à 2026-09',
    O=f'{LU} ; cohérent avec le tableau 9.3 du Bulletin BCEAO T1 2026 via usd_xof', P='Vérifié',
    Q='Moyenne mensuelle (et non fin de mois). Mois 1999 hors gabarit.')
src('gscpi', J='Collé', K='gscpi_data.xlsx, feuille « GSCPI Monthly Data », colonnes Date et GSCPI, 1998-01 à 2026-08',
    O=f'{LU} ; identique au fichier gscpi_data.xls (344 mois, écart nul)', P='Vérifié',
    Q='Série de 1998-01 à 2026-08 : septembre 2026 non publié. Le fichier .xls, identique, n\'est pas utilisé.')
src('bceao_import_food', F="BCEAO, Bulletin trimestriel des statistiques, T1 2026, tableau 9.5 « Produits alimentaires importés dans l'Union »",
    G='Indice, en FCFA (base non précisée dans le bulletin trimestriel)', J='Collé',
    K="Bulletin-Trimestriel-des-Statistiques-mars-2026.pdf, page 31 du bulletin (page 32 du PDF), colonne « Indice des prix des produits alimentaires importés », mois 2024-10 à 2026-03",
    O=f'Tableau lu le {TODAY} (extraction du texte et contrôle visuel de la page)', P='Collecté',
    Q="18 mois seulement (2024-10 à 2026-03) ; T1 2026 provisoire. Aucun historique reconstitué : les mois antérieurs restent vides. Variable de robustesse, hors échantillon principal. Les valeurs de juillet et août 2025 diffèrent de celles relevées dans le bulletin de janvier 2026 (onglet Controle, colonne I).")
src('import_food_idx', O=f'Calcul ; formule existante vérifiée le {TODAY} par recalcul indépendant',
    Q="Reconstruction : les cinq produits couvrent 57,2 % des importations alimentaires ; poids dans Parametres. Indice synthétique sans unité, chaîné géométriquement, base 100 = 2000-01. Il agrège les variations de trois prix en dollars (riz, blé, sucre) et de deux indices FAO (huiles, produits laitiers). Il ne contient pas le taux de change, à la différence de bceao_import_food exprimé en FCFA : une variante en FCFA se construit dans le code avec usd_xof.")
FAO_CP = 'https://www.fao.org/faostat/en/#data/CP'
src('cpi_all_alt', F='FAOSTAT, Consumer Price Indices (CP)', G='Indice, 2015 = 100', J='Collé',
    K='FAOSTAT_data_en_10-4-2026.csv, « Consumer Prices, General Indices (2015 = 100) », 8 pays, 2000-01 à 2026-03, avec flags',
    L=FAO_CP, M='Banque mondiale, Global Database of Inflation ; FMI, CPI', O=f'{LU} ; identique aux extraits partiels fournis', P='Vérifié',
    Q="Série alternative, non substituée à cpi_all. Base différente (2015 = 100) : comparer des variations, pas des niveaux. Historique différent de celui d'EDEN à certaines dates (voir Controle).")
src('cpi_food_alt', F='FAOSTAT, Consumer Price Indices (CP)', G='Indice, 2015 = 100', J='Collé',
    K='FAOSTAT_data_en_10-4-2026.csv, « Consumer Prices, Food Indices (2015 = 100) », 8 pays, 2000-01 à 2026-03, avec flags',
    L=FAO_CP, M='Banque mondiale, Global Database of Inflation ; FMI, CPI détaillé', O=f'{LU} ; identique aux extraits partiels fournis', P='Vérifié',
    Q="Série alternative, non substituée à cpi_food. Guinée-Bissau : 2000-01 à 2002-06 imputés par FAOSTAT (flag I).")
src('quality_flag', F='FAOSTAT (flags) et contrôles de la consolidation', J='Collé',
    K='Flags de FAOSTAT_data_en_10-4-2026.csv, complétés par les codes de contrôle', L=FAO_CP, O=LU, P='Collecté',
    Q="Format : « flag FAOSTAT de cpi_all_alt | flag FAOSTAT de cpi_food_alt », puis codes séparés par « ; ». X = valeur d'une organisation externe, I = valeur imputée. DIV_ALL / DIV_FOOD : variation mensuelle EDEN et FAOSTAT écartées de plus de 2 points. EDEN_RETRO, EDEN_RUPTURE, EDEN_PLATEAU, BULL_DIFF : voir Lisez-moi. Vide : pas d'observation FAOSTAT.")
src('rain_anom', Q="Seul substitut mensuel à la production céréalière. Identifiants des jeux dans l'onglet Pays. Aucun fichier fourni lors de la consolidation du 04/10/2026 : colonne laissée vide.")
src('local_agri_supply', J='Collé', K='FAOSTAT_data_en_10-4-2026_2.csv, item « Cereals, primary » (F1717), élément Production, 8 pays, 2000 à 2024',
    O=f'{LU} ; comparé au tableau 8.1 du Bulletin BCEAO T1 2026 (CILSS)', P='Collecté',
    Q="Production annuelle par campagne : il n'existe pas de série mensuelle. Flags dans l'onglet Annuel : estimations (E) pour le Togo 2023 et 2024, le Burkina Faso 2024 et le Sénégal 2024.")
src('import_dependency', J='Collé', K='FAOSTAT_data_en_10-4-2026_1.csv, « Cereal import dependency ratio (percent) (3-year average) », 8 pays',
    O=LU, P='Collecté',
    Q="Moyenne triennale affectée à son année centrale. Couverture inégale : 2001-2022 pour BFA, CIV, NER, SEN ; 2001-2008 pour BEN, MLI, TGO ; 2001-2013 puis 2022 pour GNB. Toutes les valeurs sont estimées (flag E). Aucune extrapolation. Seule fenêtre commune aux 8 pays : 2001-2008.")
src('food_imports_share', J='Collé', K='API_TM.VAL.FOOD.ZS.UN_DS2_en_csv_v2_404666.csv, indicateur TM.VAL.FOOD.ZS.UN, 8 pays, 2000 à 2024',
    O=f'{LU} ; définition dans les fichiers Metadata', P='Collecté',
    Q="Aliments = sections 0, 1 et 4 et division 22 de la CTCI rév. 3. Années manquantes non interpolées : GNB (8 années seulement : 2003-2005 et 2014-2018), MLI (2009, 2013-2015, 2024), BFA et TGO (2006). Aucune valeur pour 2025.")
src('gdp_real', Q="Aucun fichier fourni lors de la consolidation du 04/10/2026 : colonnes laissées vides.")
# deux séries de zone ajoutées dans Monde
for k, (nm, lab, code) in enumerate([('cpi_all_umoa', 'Indice des prix a la consommation', 'ZZZSR3017M0BP'),
                                     ('cpi_food_umoa', 'Indice des prix de la fonction alimentation', 'ZZZSR3021M0BP')]):
    r = 35 + k
    vals = [nm, 'mensuelle', 'Zone', 'Zone UMOA', 'BCEAO, base de données EDEN', 'Indice, base 100 = 2023', 'P2', 'Monde', 'Collé',
            f'exportIndicateurs.csv, bloc « ENSEMBLE UMOA », ligne « {lab} » (code {code}), 1999-01 à 2026-05', EDEN_URL,
            'Bulletin BCEAO, tableau 11.1.1.a', "Agrégat de l'Union : statistiques descriptives et contrôle",
            f'{LU} ; recoupé avec le tableau 11.1.1.a du Bulletin BCEAO T1 2026', 'Collecté',
            "Ajout du 04/10/2026 (colonnes S et T de l'onglet Monde), non repris dans Data. Écarts avec le bulletin T1 2026 de 2025-01 à 2025-09 (jusqu'à 0,6 point pour l'indice global et 1,8 point pour l'alimentation), liés aux écarts du Mali et du Niger."]
    for j, v in enumerate(vals):
        c = ws.cell(r, 2 + j); c.value = v; sty(c, ws.cell(34, 2 + j))
    ws.cell(r, 12).hyperlink = EDEN_URL
ws.auto_filter.ref = 'B2:Q36'
for dv in ws.data_validations.dataValidation:
    dv.sqref = openpyxl.worksheet.cell_range.MultiCellRange('P3:P36')
# inventaire des fichiers reçus
put(ws, 'B39', f'Fichiers reçus pour la consolidation du {TODAY}', S_LAB_B)
for col, t in zip('BFKQ', ['Fichier', 'Contenu constaté', 'Utilisation', 'Remarque']):
    put(ws, f'{col}40', t, S_HEAD)
for col in 'CDEGHIJLMNOP': sty(ws[f'{col}40'], S_HEAD)
FILES = [
    ('exportIndicateurs_1.csv', 'BCEAO EDEN : IPC global et fonction alimentation, 8 pays, mensuel 1999-01 à 2026-12 (renseigné jusqu\'à 2026-05)', 'cpi_all, cpi_food (onglets pays)', 'Séparateur « ; », virgule décimale, « - » = manquant. Libellés de mois mixtes (JAN, FEV, MAR, AVR, MAI, JUN, JUL, AUG, SEP, OCT, NOV, DEC).'),
    ('exportIndicateurs.csv', 'BCEAO EDEN : mêmes indicateurs pour l\'ensemble UMOA', 'cpi_all_umoa, cpi_food_umoa (Monde)', 'Agrégat de zone, hors panel.'),
    ('FAOSTAT_data_en_10-4-2026.csv', 'FAOSTAT CP : indices généraux et alimentaires (2015 = 100), 8 pays, 2000-01 à 2026-03, 5 040 lignes, flags X et I', 'cpi_all_alt, cpi_food_alt, quality_flag', 'Fichier de référence pour FAOSTAT : complet, sans doublon.'),
    ('Consumer_price_indices_Global_National_-_Monthly_-_FAOSTAT.csv', 'Extrait FAOSTAT tronqué à 50 000 lignes : indice alimentaire seulement, 90 pays (ordre alphabétique jusqu\'à Indonesia)', 'Non utilisé (contrôle)', 'Ne contient que 4 pays de l\'UEMOA (BEN, BFA, CIV, GNB). Chaque valeur figure deux fois (deux libellés de flag). Valeurs identiques au fichier de référence.'),
    ('result.csv', 'Même extrait que le précédent, trié autrement (50 000 lignes)', 'Non utilisé (contrôle)', 'Valeurs identiques au fichier de référence.'),
    ('Consumer_price_indices_Global_National_-_Monthly_-_FAOSTAT_1.csv', 'Extrait FAOSTAT : indice général du Burkina Faso seulement (630 lignes, valeurs en double)', 'Non utilisé (contrôle)', 'Valeurs identiques au fichier de référence.'),
    ('food_price_indices_data.csv', 'FAO Food Price Index, indices nominaux mensuels 2014-2016 = 100, 1990-01 à 2026-09', 'fao_food, fao_cereals, fao_oils, fao_sugar, fao_dairy, fao_meat', 'Deux lignes de titre avant l\'en-tête.'),
    ('CMO-Historical-Data-Monthly.xlsx', 'Banque mondiale, Pink Sheet, prix mensuels nominaux en dollars, 1960M01 à 2026M09 (mise à jour du 02/10/2026)', 'oil_usd, rice_thai, wheat_hrw, palm_oil, sugar_world, maize', 'Feuille Monthly Prices. La feuille « Mismatch Details » liste 152 écarts avec une autre version du fichier (orge et sorgho surtout) : aucune des six séries retenues n\'est concernée.'),
    ('ECB_Data_Portal_20261004111939.csv', 'BCE, EXR.M.USD.EUR.SP00.A, moyenne mensuelle, 1999-01 à 2026-09', 'eur_usd (puis usd_xof par formule)', ''),
    ('gscpi_data.xlsx', 'Fed de New York, GSCPI mensuel, 1998-01 à 2026-08', 'gscpi', 'Feuille « GSCPI Monthly Data ».'),
    ('gscpi_data.xls', 'Même contenu que le fichier .xlsx', 'Non utilisé', 'Identique au .xlsx sur les 344 mois.'),
    ('FAOSTAT_data_en_10-4-2026_2.csv', 'FAOSTAT QCL : céréales par produit (surface, rendement, production), 8 pays, 1961 à 2024', 'local_agri_supply et flags (Annuel)', 'Seules les lignes « Cereals, primary » / Production sont reprises.'),
    ('FAOSTAT_data_en_10-4-2026_1.csv', 'FAOSTAT FS : taux de dépendance aux importations céréalières, moyennes triennales 2000-2002 à 2021-2023, 126 lignes', 'import_dependency et flags (Annuel)', 'Toutes les valeurs sont estimées (flag E).'),
    ('API_TM.VAL.FOOD.ZS.UN_DS2_en_csv_v2_404666.csv', 'Banque mondiale WDI : importations alimentaires en % des importations de marchandises, 1960 à 2025', 'food_imports_share (Annuel)', '4 lignes d\'en-tête avant les noms de colonnes.'),
    ('Metadata_Indicator_API_TM.VAL.FOOD.ZS.UN_DS2_en_csv_v2_404666.csv', 'Définition et source de l\'indicateur TM.VAL.FOOD.ZS.UN', 'Documentation', 'Source : UN Comtrade, WITS, estimations de la Banque mondiale.'),
    ('Metadata_Country_API_TM.VAL.FOOD.ZS.UN_DS2_en_csv_v2_404666.csv', 'Région et groupe de revenu par pays', 'Documentation', 'Aucune note particulière pour les 8 pays.'),
    ('Bulletin-Trimestriel-des-Statistiques-mars-2026.pdf', 'BCEAO, Bulletin trimestriel des statistiques, premier trimestre 2026 (52 pages)', 'bceao_import_food (tableau 9.5) ; contrôles (tableaux 8.1, 9.3, 9.4, 11.1.x)', 'Les tableaux 11.1.x.a donnent l\'IHPC base 100 = 2023 par pays de 2024-07 à 2026-03.'),
]
for k, (f, c, u, rm) in enumerate(FILES):
    r = 41 + k
    put(ws, f'B{r}', f, S_LAB); put(ws, f'F{r}', c, S_LAB); put(ws, f'K{r}', u, S_LAB); put(ws, f'Q{r}', rm or None, S_LAB)

# ================================================================== 6. LISEZ-MOI
ws = wb['Lisez-moi']
mm25 = {iso: jan[(iso, 'cpi_food')][0] for iso in ISO}
ws['C5'] = (f"Consolidé le {TODAY} à partir des fichiers bruts fournis (BCEAO EDEN, FAOSTAT, FAO, Banque mondiale, BCE, Fed de New York, Bulletin BCEAO T1 2026). "
            "Séries mensuelles et annuelles renseignées en niveau ; restent vides rain_anom et gdp_real (aucun fichier fourni). Fichier d'origine du 02/10/2026 conservé intact.")
ws['C7'] = "Onglet Monde : fao_food et sous-indices FAO, oil_usd et prix par produit (Pink Sheet), eur_usd (BCE), gscpi (Fed de New York), bceao_import_food (18 mois). Fait le 04/10/2026."
ws['C8'] = "Onglets pays (BEN, BFA, CIV, GNB, MLI, NER, SEN, TGO) : cpi_all et cpi_food viennent de BCEAO EDEN (séries principales) ; cpi_all_alt et cpi_food_alt de FAOSTAT (séries alternatives). Fait le 04/10/2026."
ws['C9'] = "Onglet Suivi : la ligne « Baseline prête à lancer » et le tableau de couverture par variable se mettent à jour par formules. Le code peut tourner sur l'onglet Data."
ws['C10'] = "Onglet Annuel renseigné (production céréalière, dépendance aux importations, part des importations alimentaires). Restent à collecter : rain_anom, gdp_real, historique de bceao_import_food."
ws['C18'] = "En-tête en ligne 2 (sauter la ligne 1). Clés : iso3 et Date. Une cellule vide signifie valeur manquante. Les logarithmes, variations et retards se calculent dans le code. Sous R : readxl::read_excel(fichier, sheet = \"Data\", skip = 1, na = \"\")."
ws['C23'] = ("IHPC passé de la base 2014 à la base 2023 en janvier 2025. EDEN publie les séries en base 100 = 2023 sur tout l'historique : pas de saut d'échelle, mais nomenclature et pondérations changent en 2025-01 "
             f"(cpi_food sur le mois : {fr(mm25['GNB'])} % en Guinée-Bissau, {fr(mm25['TGO'])} % au Togo, {fr(mm25['NER'])} % au Niger). Aucun raccord n'a été fait : échantillon principal arrêté à 2024-12.")
ws['C24'] = "Les flags FAOSTAT portent désormais sur les séries alternatives (cpi_all_alt, cpi_food_alt) et sont reportés dans quality_flag. Seule la Guinée-Bissau a des mois imputés (cpi_food_alt, 2000-01 à 2002-06)."
ws['C25'] = "bceao_import_food : seuls les 18 mois du tableau 9.5 du Bulletin trimestriel T1 2026 sont renseignés (2024-10 à 2026-03). L'historique long reste à reconstituer. import_food_idx en est une reconstruction : indice synthétique sans unité, bâti sur des prix et indices internationaux, sans taux de change."
ws['C26'] = ("Onglet Controle : l'alignement des dates est tranché. usd_xof calculé coïncide avec le tableau 9.3 du Bulletin T1 2026 ; les valeurs de change et de pétrole relevées dans le bulletin de janvier 2026 (colonnes C et F) étaient décalées. "
             "Les inflations par pays reprises de l'autre fichier concordent avec cpi_all.")
def fpct(iso):
    f = fcp[(iso, 'cpi_all_alt')]; return 100 * (f['2008-01'] / f['2007-12'] - 1)


V5 = ("EDEN, sauts aux changements de base : en 2008-01, cpi_all augmente sur le mois de "
      + ", ".join(f"{fr(pct(i, 'cpi_all', '2008-01'))} % ({NAMES[i]})" for i in ['CIV', 'MLI', 'BFA', 'NER', 'BEN'])
      + ", contre " + ", ".join(f"{fr(fpct(i))} %" for i in ['CIV', 'MLI', 'BFA', 'NER', 'BEN'])
      + " dans FAOSTAT. Audit du 04/10/2026 (Controle, section J) : hors fenêtres de 1 à 2 ans après chaque changement de base, les deux sources sont la même série ; dans la fenêtre de 2008, EDEN concentre la hausse en janvier puis aplatit le profil. Une indicatrice ne suffit donc pas. Traitement proposé, à valider : variations FAOSTAT dans six fenêtres autour de 2008.")
NEW = [
    None,
    ('Consolidation', f"Faite le {TODAY}. Fichier produit : 20261004_final_data_project_research_UEMOA_consolidated.xlsx. Structure d'origine conservée (17 onglets, mêmes colonnes, mêmes formules)."),
    ('Ajouts de structure', "Monde : colonnes S et T (cpi_all_umoa, cpi_food_umoa, agrégat EDEN de l'Union, hors Data). Annuel : colonnes AH à AW (flags FAOSTAT). Suivi, Controle et Source : tableaux ajoutés sous l'existant."),
    ('Convention, niveaux', "Toutes les séries sont en niveau, dans l'unité de la source. Aucune inflation, variation, différence de logarithmes, retard ou choc n'est calculé dans le classeur."),
    ('Convention, manquants', "Une valeur manquante est une cellule vide, jamais un zéro. Aucune interpolation, aucune extrapolation, aucun prolongement de série."),
    ('Convention, dates', "Mois au format texte AAAA-MM, de 2000-01 à 2026-09 (321 mois). Les observations de 1999 (EDEN, BCE) et antérieures à 2000 (FAO, Pink Sheet, GSCPI) existent dans les fichiers bruts mais sont hors gabarit."),
    ('Convention, sources en conflit', "Les deux séries sont conservées : EDEN en cpi_all et cpi_food, FAOSTAT en cpi_all_alt et cpi_food_alt. Les bases diffèrent (2023 = 100 et 2015 = 100) : aucune n'a été rebasée ni raccordée."),
    ('Convention, annuel', "Dans Data, la valeur annuelle est répétée sur les 12 mois de l'année. import_dependency (moyenne sur 3 ans) est affecté à l'année centrale."),
    ('quality_flag, lecture', "« X|X » : flags FAOSTAT de cpi_all_alt puis de cpi_food_alt (X = valeur d'une organisation externe, I = valeur imputée par FAOSTAT). Des codes de contrôle suivent, séparés par « ; ». Vide : aucune observation FAOSTAT ce mois-là."),
    ('quality_flag, codes', "DIV_ALL, DIV_FOOD : la variation mensuelle diffère de plus de 2 points entre EDEN et FAOSTAT (indice global, alimentation). EDEN_RETRO : Guinée-Bissau avant 2002-07, cpi_all proportionnel à celui de la Côte d'Ivoire. EDEN_RUPTURE : Guinée-Bissau 2002-07, saut de niveau. EDEN_PLATEAU : valeur répétée au moins 4 mois. BULL_DIFF : EDEN diffère du Bulletin BCEAO T1 2026."),
    ('ihpc_base (Data)', "Indique le régime de l'IHPC (« avant 2025 » ou « base 2023 »), c'est-à-dire la nomenclature et les pondérations, et non l'année de référence de l'indice, qui est 2023 sur toute la période dans EDEN."),
    ('Statut (onglet Source)', "« Collecté » : série chargée depuis le fichier indiqué. « Vérifié » : série en outre recoupée avec une seconde source fournie. « À collecter » : aucun fichier fourni."),
    ('Vigilance 5', V5),
    ('Vigilance 6', "Guinée-Bissau : avant 2002-07, cpi_all d'EDEN vaut 0,958 à 0,960 fois celui de la Côte d'Ivoire (rétropolation probable), puis saute de 13,6 % en 2002-07 ; cpi_food ne commence qu'en 2002-07. À exclure ou à traiter à part."),
    ('Vigilance 7', "Révisions 2025 : EDEN diffère du Bulletin T1 2026 pour le Mali (surtout de 2025-03 à 2025-09, jusqu'à 1,7 point sur l'indice global et 3,5 points sur l'alimentation) et le Niger (2025-03 à 2025-05, jusqu'à 6,8 points sur l'alimentation en 2025-04). Sénégal, cpi_food 2025-10 : creux isolé (107,7 puis 100,7 puis 106,4). Tous ces mois sont postérieurs à l'échantillon principal."),
    ('Vigilance 8', "import_dependency ne couvre que 2001-2008 pour le Bénin, le Mali et le Togo : pour une interaction, la seule fenêtre commune aux 8 pays est 2001-2008. food_imports_share n'a que 8 observations pour la Guinée-Bissau (2003-2005 et 2014-2018)."),
    ('Contrôles', "Onglet Suivi, à partir de la ligne 39 : couverture de chaque variable (source, première et dernière observation, nombre d'observations et de manquants, remarques). Onglet Controle, à partir de la ligne 20 : contrôles de qualité, recoupements avec le Bulletin BCEAO, ruptures et valeurs extrêmes, audit EDEN / FAOSTAT aux changements de base (section J)."),
]
r0 = 27
for k, it in enumerate(NEW):
    if it is None: continue
    put(ws, f'B{r0 + k}', it[0], S_LAB_B); put(ws, f'C{r0 + k}', it[1], S_LAB)
    ws.row_dimensions[r0 + k].height = 13.0
LISEZ_V5_ROW = r0 + [i for i, it in enumerate(NEW) if it and it[0] == 'Vigilance 5'][0]


# ================================================================== 7. SUIVI : couverture par variable
ws = wb['Suivi']
put(ws, 'B38', f'Couverture par variable (consolidation du {TODAY}) : comptages par formules sur le gabarit 2000-01 à 2026-09 (321 mois) ou 2000 à 2026 (27 années)', S_LAB_B)
for col, t in zip('BCDEFGHI', ['Variable', 'Onglet', 'Source', 'Première observation', 'Dernière observation',
                                'Observations non manquantes', 'Valeurs manquantes', 'Remarques / problèmes']):
    put(ws, f'{col}39', t, S_HEAD)
HM = hdr_map(wb['Monde'])
n_flag = {iso: {t: int(sum(t in (flag[iso][d] or '').split(';') for d in M)) for t in ['DIV_ALL', 'DIV_FOOD', 'BULL_DIFF', 'EDEN_PLATEAU']} for iso in ISO}
FPI_R = 'Complet, aucun trou. Fichier disponible depuis 1990-01 (mois antérieurs hors gabarit).'
PK_R = 'Complet, aucun trou. Unité d\'origine : '
MONDE_ROWS = [
    ('fao_food', 'FAO, Food Price Index', FPI_R), ('fao_cereals', 'FAO, Food Price Index', FPI_R), ('fao_oils', 'FAO, Food Price Index', FPI_R),
    ('fao_sugar', 'FAO, Food Price Index', FPI_R), ('fao_dairy', 'FAO, Food Price Index', FPI_R), ('fao_meat', 'FAO, Food Price Index', FPI_R),
    ('oil_usd', 'Banque mondiale, Pink Sheet', PK_R + 'USD par baril. Variations extrêmes en 2008-10, 2008-11, 2020-03, 2020-04 et 2026-03 (valeurs de la source).'),
    ('rice_thai', 'Banque mondiale, Pink Sheet', PK_R + 'USD par tonne. Flambée de 2008-02 à 2008-04.'),
    ('wheat_hrw', 'Banque mondiale, Pink Sheet', PK_R + 'USD par tonne.'),
    ('palm_oil', 'Banque mondiale, Pink Sheet', PK_R + 'USD par tonne. Définition de la série modifiée en 2001-12, 2021-01, 2024-11, 2025-02 et 2026-01 (voir Source).'),
    ('sugar_world', 'Banque mondiale, Pink Sheet', PK_R + 'USD par kg. Valeur répétée 5 mois en 2007 (0,22) et 4 mois en 2017 (0,32), prix arrondi à 2 décimales.'),
    ('maize', 'Banque mondiale, Pink Sheet', PK_R + 'USD par tonne.'),
    ('eur_usd', 'BCE, Data Portal', 'Complet, aucun trou. Fichier disponible depuis 1999-01.'),
    ('usd_xof', 'Calcul (formule)', 'Formule 655,957 / eur_usd. Coïncide avec le tableau 9.3 du Bulletin BCEAO T1 2026.'),
    ('gscpi', 'Fed de New York', 'Septembre 2026 non publié (fichier arrêté à 2026-08). Aucun trou interne.'),
    ('bceao_import_food', 'BCEAO, Bulletin T1 2026, tab. 9.5', '18 mois seulement. Aucun historique dans les fichiers fournis ; rien n\'a été reconstitué.'),
    ('import_food_idx', 'Calcul (formule)', 'Formule existante, pondérations de l\'onglet Parametres. Indice synthétique sans unité, base 100 = 2000-01, sans taux de change.'),
    ('cpi_all_umoa', 'BCEAO EDEN', 'Agrégat de l\'Union, hors Data. 2026-06 à 2026-09 non publiés. Diffère du Bulletin T1 2026 de 2025-01 à 2025-09.'),
    ('cpi_food_umoa', 'BCEAO EDEN', 'Agrégat de l\'Union, hors Data. 2026-06 à 2026-09 non publiés. Diffère du Bulletin T1 2026 de 2025-01 à 2025-09.'),
]
rows = []
for var, source, rem in MONDE_ROWS:
    rows.append((var, 'Monde', source, 'Monde', L(HM[var]), 3, 323, rem))


def cpi_rem(iso, var):
    t = '2026-06 à 2026-09 non publiés dans EDEN. Aucun trou interne.'
    k = 'DIV_ALL' if var == 'cpi_all' else 'DIV_FOOD'
    if iso == 'GNB' and var == 'cpi_all': t += ' Avant 2002-07 : rétropolation probable (proportionnel à la Côte d\'Ivoire), puis saut de 13,6 % en 2002-07.'
    if iso == 'GNB' and var == 'cpi_food': t = 'Série absente d\'EDEN avant 2002-07 (30 mois manquants, non comblés). 2026-06 à 2026-09 non publiés.'
    t += f' {n_flag[iso][k]} mois où la variation mensuelle s\'écarte de plus de 2 points de FAOSTAT.'
    if n_flag[iso]['BULL_DIFF']: t += f' {n_flag[iso]["BULL_DIFF"]} mois différents du Bulletin BCEAO T1 2026.'
    if iso == 'BEN' and var == 'cpi_food': t += ' Valeur répétée de 2017-04 à 2017-07 (93,0) puis de 2017-08 à 2018-01 (92,9).'
    if iso == 'SEN' and var == 'cpi_food': t += ' Creux isolé en 2025-10 (100,7).'
    return t


for var, source in [('cpi_all', 'BCEAO EDEN'), ('cpi_food', 'BCEAO EDEN'), ('cpi_all_alt', 'FAOSTAT CP'), ('cpi_food_alt', 'FAOSTAT CP'),
                    ('quality_flag', 'FAOSTAT et contrôles'), ('rain_anom', 'Non collecté')]:
    for iso in ISO:
        Hc = hdr_map(wb[iso])
        if var in ('cpi_all', 'cpi_food'): rem = cpi_rem(iso, var)
        elif var == 'cpi_all_alt': rem = 'FAOSTAT arrêté à 2026-03. Aucun trou. Flag X (valeur d\'une organisation externe) sur tous les mois. Base 2015 = 100.'
        elif var == 'cpi_food_alt': rem = 'FAOSTAT arrêté à 2026-03. Aucun trou. ' + ('30 mois imputés par FAOSTAT (flag I), de 2000-01 à 2002-06.' if iso == 'GNB' else 'Flag X sur tous les mois.') + ' Base 2015 = 100.'
        elif var == 'quality_flag': rem = 'Texte. Renseigné pour chaque mois où FAOSTAT a une observation (jusqu\'à 2026-03).'
        else: rem = 'Aucun fichier fourni : colonne laissée vide.'
        rows.append((var, iso, source, iso, L(Hc[var]), 3, 323, rem))
HA = hdr_map(wb['Annuel'])
dep = annuel['import_dependency']; fis = annuel['food_imports_share']; pfl = annuel['local_agri_supply_flag']
for var, source in [('local_agri_supply', 'FAOSTAT QCL'), ('import_dependency', 'FAOSTAT FS'), ('food_imports_share', 'Banque mondiale, WDI'), ('gdp_real', 'Non collecté')]:
    for iso in ISO:
        if var == 'local_agri_supply':
            e = [str(y) for y in YEARS if pfl.loc[y, iso] == 'E']
            rem = 'Tonnes. 2025 et 2026 non publiés. ' + ('Valeurs officielles (flag A).' if not e else f'Valeur estimée (flag E) en {" et ".join(e)}, officielle ailleurs.')
        elif var == 'import_dependency':
            ys = [y for y in YEARS if pd.notna(dep.loc[y, iso])]; gaps = [y for y in range(ys[0], ys[-1] + 1) if y not in ys]
            rem = f'Moyenne sur 3 ans affectée à l\'année centrale. Toutes les valeurs estimées (flag E). ' + (f'Trou de {gaps[0]} à {gaps[-1]}. ' if gaps else '') + 'Non extrapolé.'
        elif var == 'food_imports_share':
            ys = [y for y in range(2000, 2025) if pd.isna(fis.loc[y, iso])]
            rem = ('Années manquantes entre 2000 et 2024 : ' + ', '.join(map(str, ys)) + '. ' if ys else 'Complet de 2000 à 2024. ') + '2025 et 2026 non publiés. Non interpolé.'
        else: rem = 'Aucun fichier fourni : colonne laissée vide.'
        rows.append((var, f'Annuel ({iso})', source, 'Annuel', L(HA[f'{var}_{iso}']), 3, 29, rem))
for k, (var, onglet, source, sh, col, r1, r2, rem) in enumerate(rows):
    r = 40 + k; rg = f'{sh}!${col}${r1}:${col}${r2}'; dt = f'{sh}!$A${r1}:$A${r2}'
    put(ws, f'B{r}', var, S_LAB); put(ws, f'C{r}', onglet, S_LAB); put(ws, f'D{r}', source, S_LAB)
    put(ws, f'E{r}', f'=IF(G{r}=0,"-",INDEX({dt},MATCH(TRUE(),INDEX({rg}<>"",0),0)))', S_FORM, 'General')
    put(ws, f'F{r}', f'=IF(G{r}=0,"-",INDEX({dt},SUMPRODUCT(MAX(({rg}<>"")*(ROW({rg})-{r1 - 1})))))', S_FORM, 'General')
    put(ws, f'G{r}', f'=SUMPRODUCT(({rg}<>"")*1)', S_FORM, 'General')
    put(ws, f'H{r}', f'=ROWS({rg})-G{r}', S_FORM, 'General')
    put(ws, f'I{r}', rem, S_LAB)
SUIVI_LAST = 40 + len(rows) - 1
set_width(ws, 'G', 28)

# ================================================================== 8. CONTROLE
ws = wb['Controle']
S_NOTE = ws['B12']
S1 = pd.read_pickle('bull_tabs.pkl') if False else None
put(ws, 'B18', (f"Mise à jour du {TODAY} : l'alignement est tranché. La colonne D (655,957 / eur_usd) coïncide avec le tableau 9.3 du Bulletin trimestriel T1 2026 (écart maximal {fr(usd_maxdiff, 4)} %). "
                "Les valeurs des colonnes C et F, lues dans le bulletin de janvier 2026, étaient décalées (581,3 correspond à mai 2025 : 581,6 au tableau 9.3). "
                "Les inflations de l'autre fichier (colonnes J à X) concordent avec cpi_all. Contrôles complets ci-dessous."), S_NOTE)
r = 20
put(ws, f'B{r}', f'CONTRÔLES DE LA CONSOLIDATION DU {TODAY}', S_LAB_B)
INDEX_ROW = r + 1
r = 33
sections = []


def title(r, text, sub=None):
    put(ws, f'B{r}', text, S_LAB_B)
    if sub: put(ws, f'B{r + 1}', sub, S_NOTE)
    sections.append((text, r))
    return r + (2 if sub else 1)


def header(r, labels, start=2):
    for k, t in enumerate(labels): put(ws, f'{L(start + k)}{r}', t, S_HEAD)
    return r + 1


# ---------- A. Dix contrôles
r = title(r, 'A. Contrôles de qualité', 'Colonne D, en turquoise : formule recalculée à chaque ouverture. En gris : résultat figé, obtenu par script le 04/10/2026.')
r = header(r, ['N°', 'Contrôle', 'Résultat', 'Attendu', 'Méthode', None, None, 'Commentaire'])
SH_ERR = '+'.join([f'SUMPRODUCT(ISERROR({s}!$A$3:$Y$323)*1)' for s in ISO] + ['SUMPRODUCT(ISERROR(Data!$A$3:$AH$2570)*1)', 'SUMPRODUCT(ISERROR(Monde!$A$3:$T$323)*1)',
                                                                              'SUMPRODUCT(ISERROR(Annuel!$A$3:$AW$29)*1)', f'SUMPRODUCT(ISERROR(Suivi!$B$3:$I${SUIVI_LAST})*1)'])
SUM_ISO = '+'.join(f'SUM({s}!$B$3:$C$323)+SUM({s}!$U$3:$V$323)' for s in ISO)
n_rupt = int(AN.type.isin(['Début de série (GNB)', 'Rétropolation EDEN (GNB)']).sum() + AN.type.str.contains('Changement de base|Passage').sum())
n_ext_c = int(AN.crit.str.contains('extrême').sum()); n_div_c = int(AN.crit.str.contains('divergence').sum())
exp_cov = 8 * 317 - 30
CHECKS = [
    ('Doublons pays × mois', '=SUMPRODUCT((COUNTIFS(Data!$B$3:$B$2570,Data!$B$3:$B$2570,Data!$A$3:$A$2570,Data!$A$3:$A$2570)>1)*1)', 0,
     'Lignes de Data dont la clé iso3 × Date apparaît plus d\'une fois', 'Aucun doublon. Dans les sources : les trois extraits FAOSTAT redondants (valeurs en double) ont été écartés au profit du fichier complet.'),
    ('Dates', '=SUMPRODUCT((LEN(Data!$A$3:$A$2570)<>7)+(MID(Data!$A$3:$A$2570,5,1)<>"-"))', 0,
     'Dates de Data qui ne sont pas au format AAAA-MM', '321 mois consécutifs par pays, de 2000-01 à 2026-09, 8 pays, 2 568 lignes : séquence vérifiée par script dans Monde, les 8 onglets pays et Data.'),
    ('Valeurs manquantes', '=SUMPRODUCT((Data!$A$3:$A$2570<=Parametres!$C$5)*((Data!$D$3:$D$2570="")+(Data!$E$3:$E$2570="")))', 30,
     'cpi_all ou cpi_food manquant sur l\'échantillon principal (jusqu\'à 2024-12)', 'Les 30 cas sont cpi_food de la Guinée-Bissau, 2000-01 à 2002-06. Détail de chaque variable dans l\'onglet Suivi (ligne 39 et suivantes). Aucun trou interne dans les autres séries.'),
    ('Valeurs nulles suspectes', '=SUMPRODUCT(ISNUMBER(Monde!$B$3:$T$323)*(Monde!$B$3:$T$323=0))+SUMPRODUCT(ISNUMBER(Data!$D$3:$X$2570)*(Data!$D$3:$X$2570=0))+SUMPRODUCT(ISNUMBER(Annuel!$B$3:$AG$29)*(Annuel!$B$3:$AG$29=0))', 0,
     'Valeurs numériques égales à zéro dans Monde, Data (colonnes D à X) et Annuel', 'Aucun zéro : les manquants sont des cellules vides. Les « - » d\'EDEN et les « … » du Pink Sheet sont traités comme manquants.'),
    ('Ruptures de série', n_rupt, None,
     'Lignes de la section G : début de série, rétropolation, changement de base', 'Guinée-Bissau : cpi_all rétropolé avant 2002-07 et saut de 13,6 % en 2002-07. Sauts d\'EDEN en 2008-01 et 2017-01 absents de FAOSTAT. Voir sections E, F, G et l\'audit en section J.'),
    ('Changements de base', 'voir E', None,
     'Moyenne annuelle 2023 de chaque série EDEN ; variation de 2024-12 à 2025-01', 'EDEN : base 100 = 2023 sur tout l\'historique (moyenne 2023 comprise entre 99,99 et 100,01). FAOSTAT : 2015 = 100. Passage à l\'IHPC base 2023 en 2025-01 : voir section E. Séries non raccordées entre elles.'),
    ('Valeurs extrêmes', n_ext_c, None,
     'Variation mensuelle des IPC à plus de 4 écarts-types robustes (MAD)', f'{n_ext_c} mois-pays signalés pour les IPC (section G) ; séries mondiales en section H. Valeurs conservées telles que publiées.'),
    ('Couverture', '=Suivi!$C$36', exp_cov,
     'Lignes de Data avec cpi_food et fao_food renseignés', 'Soit 317 mois pour 7 pays et 287 pour la Guinée-Bissau. Couverture de chaque variable dans l\'onglet Suivi.'),
    ('Formules Excel', '=' + SH_ERR, 0,
     'Cellules en erreur dans Monde, les 8 onglets pays, Annuel, Data et Suivi', 'Recalcul complet du classeur le 04/10/2026 : aucune erreur de formule (référence, valeur, nom, division par zéro, valeur non disponible).'),
    ('Cohérence entre onglets', f'=ROUND(ABS(SUM(Data!$F$3:$V$2570)-8*SUM(Monde!$B$3:$R$323))+ABS(SUM(Data!$D$3:$E$2570)+SUM(Data!$W$3:$X$2570)-({SUM_ISO})),4)', 0,
     'Sommes des colonnes de Data comparées à Monde et aux onglets pays', 'Comparaison cellule à cellule par script en complément : aucun écart entre Monde, les onglets pays, Annuel, Pays et Data.'),
    ('Fidélité aux fichiers sources', 0, 0,
     'Relecture indépendante des fichiers bruts, comparée au classeur (script)', 'Toutes les valeurs chargées ont été relues dans les fichiers bruts par un second programme : aucun écart. S\'y ajoute un tirage aléatoire de 80 observations.'),
]
A_FIRST = r
for k, (lab, res, exp, meth, com) in enumerate(CHECKS):
    put(ws, f'B{r}', k + 1, S_LAB); put(ws, f'C{r}', lab, S_LAB)
    put(ws, f'D{r}', res, S_FORM if isinstance(res, str) and res.startswith('=') else S_PRE, 'General')
    put(ws, f'E{r}', exp if exp is not None else '-', S_PRE, 'General')
    put(ws, f'F{r}', meth, S_LAB); put(ws, f'I{r}', com, S_LAB)
    r += 1
r += 1

# ---------- B. Change, pétrole, indice BCEAO : bulletin T1 2026
r = title(r, 'B. Recoupement avec le Bulletin trimestriel BCEAO T1 2026 : change, pétrole, produits alimentaires importés',
          'Tableaux 9.3, 9.4 et 9.5. Le pétrole du bulletin est une cotation de New York : un écart de quelques pour cent avec le Brent est attendu.')
r = header(r, ['Date', 'usd_xof, bulletin (tab. 9.3)', 'usd_xof, classeur', 'Écart (%)', 'Pétrole, bulletin (tab. 9.4, USD par baril)', 'oil_usd, classeur (Brent)', 'Écart (%)',
               'bceao_import_food, bulletin (tab. 9.5)', 'bceao_import_food, classeur', 'Écart'])
bimp = monde['bceao_import_food'].dropna()
for d in bull_usd.index:
    put(ws, f'B{r}', d, S_LAB); put(ws, f'C{r}', float(bull_usd[d]), S_PRE, '0.0000')
    put(ws, f'D{r}', f'=IF(Monde!$O${ROW[d]}="","",Monde!$O${ROW[d]})', S_FORM, '0.0000'); put(ws, f'E{r}', f'=IF(D{r}="","",100*(D{r}/C{r}-1))', S_FORM, '0.0000')
    if d in bull_oil.index:
        put(ws, f'F{r}', float(bull_oil[d]), S_PRE, '0.00'); put(ws, f'G{r}', f'=IF(Monde!$H${ROW[d]}="","",Monde!$H${ROW[d]})', S_FORM, '0.00')
        put(ws, f'H{r}', f'=IF(G{r}="","",100*(G{r}/F{r}-1))', S_FORM, '0.0')
    put(ws, f'I{r}', float(bimp[d]), S_PRE, '0.00'); put(ws, f'J{r}', f'=IF(Monde!$Q${ROW[d]}="","",Monde!$Q${ROW[d]})', S_FORM, '0.00')
    put(ws, f'K{r}', f'=IF(J{r}="","",J{r}-I{r})', S_FORM, '0.00')
    r += 1
r += 1

# ---------- C. IHPC bulletin vs EDEN
r = title(r, 'C. IHPC du Bulletin BCEAO T1 2026 (tableaux 11.1.1.a à 11.1.9.a, base 100 = 2023) et séries EDEN du classeur',
          f"Indice global et division 1 (produits alimentaires et boissons non alcoolisées). Pays : {n_cmp - n_diff} mois-pays sur {n_cmp} identiques à 0,05 point près ; {n_diff} diffèrent (Mali, Niger, Burkina Faso). UMOA : agrégat (colonnes S et T de Monde).")
r = header(r, ['Date', 'iso3', 'IHPC global, bulletin', 'cpi_all, classeur', 'Écart (points)', 'Division 1, bulletin', 'cpi_food, classeur', 'Écart (points)'])
C_FIRST = r
for _, x in b.iterrows():
    rr = ROW[x.date]
    ra, rf = (f'Monde!$S${rr}', f'Monde!$T${rr}') if x.iso3 == 'UMOA' else (f'{x.iso3}!$B${rr}', f'{x.iso3}!$C${rr}')
    put(ws, f'B{r}', x.date, S_LAB); put(ws, f'C{r}', x.iso3, S_LAB)
    put(ws, f'D{r}', float(x.ihpc_global), S_PRE, '0.0'); put(ws, f'E{r}', f'=IF({ra}="","",{ra})', S_FORM, '0.0'); put(ws, f'F{r}', f'=IF(E{r}="","",E{r}-D{r})', S_FORM, '0.0')
    put(ws, f'G{r}', float(x.ihpc_div1), S_PRE, '0.0'); put(ws, f'H{r}', f'=IF({rf}="","",{rf})', S_FORM, '0.0'); put(ws, f'I{r}', f'=IF(H{r}="","",H{r}-G{r})', S_FORM, '0.0')
    r += 1
C_LAST = r - 1
put(ws, f'B{r}', 'Écart absolu maximal', S_LAB_B); put(ws, f'F{r}', f'=SUMPRODUCT(MAX(ABS(F{C_FIRST}:F{C_LAST})))', S_FORM, '0.0'); put(ws, f'I{r}', f'=SUMPRODUCT(MAX(ABS(I{C_FIRST}:I{C_LAST})))', S_FORM, '0.0')
r += 2

# ---------- D. Inflation par pays, tableau 11.1.11
i0 = next(k for k, l in enumerate(BTXT) if 'Tableau 11.1.11' in l)
T11 = {}
ZN = {'Bénin': 'BEN', 'Burkina': 'BFA', "Côte d'Ivoire": 'CIV', 'Guinée-Bissau': 'GNB', 'Mali': 'MLI', 'Niger': 'NER', 'Sénégal': 'SEN', 'Togo': 'TGO', 'UEMOA': 'UMOA'}
for l in BTXT[i0:i0 + 30]:
    m = re.match(r"\s*([A-Za-zéèôÉ' \-]+?)\s{3,}(-?\d+,\d)\s+(-?\d+,\d)\s+(-?\d+,\d)\s+(-?\d+,\d)\s+(-?\d+,\d)\s+(-?\d+,\d)\s*$", l)
    if m and m.group(1).strip() in ZN: T11[ZN[m.group(1).strip()]] = [float(x.replace(',', '.')) for x in m.groups()[1:]]
assert len(T11) == 9, T11
PER = [('2025 (moyenne annuelle)', '2025-01', '2025-12'), ('T1-2025', '2025-01', '2025-03'), ('T2-2025', '2025-04', '2025-06'),
       ('T3-2025', '2025-07', '2025-09'), ('T4-2025', '2025-10', '2025-12'), ('T1-2026', '2026-01', '2026-03')]
r = title(r, 'D. Inflation en glissement annuel par pays : Bulletin BCEAO T1 2026 (tableau 11.1.11) et classeur',
          "Classeur : moyenne de cpi_all sur la période rapportée à la même période un an plus tôt. Les écarts visibles concernent le Mali, le Niger et l'UMOA (révisions de 2025, voir section C).")
r = header(r, ['Zone', 'Période', 'Inflation, bulletin (%)', 'Inflation, classeur (%)', 'Écart (points)'])
for z in ['BEN', 'BFA', 'CIV', 'GNB', 'MLI', 'NER', 'SEN', 'TGO', 'UMOA']:
    for k, (lab, a, zz) in enumerate(PER):
        r1, r2 = ROW[a], ROW[zz]; sh, cl = ('Monde', 'S') if z == 'UMOA' else (z, 'B')
        put(ws, f'B{r}', z, S_LAB); put(ws, f'C{r}', lab, S_LAB); put(ws, f'D{r}', T11[z][k], S_PRE, '0.0')
        put(ws, f'E{r}', f'=100*(AVERAGE({sh}!${cl}${r1}:${cl}${r2})/AVERAGE({sh}!${cl}${r1 - 12}:${cl}${r2 - 12})-1)', S_FORM, '0.0')
        put(ws, f'F{r}', f'=E{r}-D{r}', S_FORM, '0.0')
        r += 1
r += 1

# ---------- E. Passage à la base 2023
r = title(r, 'E. Passage à l\'IHPC base 2023 : variation de 2024-12 à 2025-01 dans EDEN',
          "Colonnes G et H : moyenne et écart-type des variations de décembre à janvier de 2001 à 2024 (figés, script). Une variation éloignée de plus de 2 écarts-types de la moyenne est signalée.")
r = header(r, ['iso3', 'Variable', 'Valeur 2024-12', 'Valeur 2025-01', 'Variation (%)', 'Moyenne des variations de janvier, 2001-2024 (%)', 'Écart-type (%)', 'Lecture'])
for iso in ISO:
    for var, col in [('cpi_all', 'B'), ('cpi_food', 'C')]:
        v, mu, sd = jan[(iso, var)]
        put(ws, f'B{r}', iso, S_LAB); put(ws, f'C{r}', var, S_LAB)
        put(ws, f'D{r}', f"={iso}!${col}${ROW['2024-12']}", S_FORM, '0.0'); put(ws, f'E{r}', f"={iso}!${col}${ROW['2025-01']}", S_FORM, '0.0')
        put(ws, f'F{r}', f'=100*(E{r}/D{r}-1)', S_FORM, '0.00'); put(ws, f'G{r}', round(mu, 2), S_PRE, '0.00'); put(ws, f'H{r}', round(sd, 2), S_PRE, '0.00')
        put(ws, f'I{r}', 'Hors norme (plus de 2 écarts-types)' if abs(v - mu) > 2 * sd else 'Dans la norme des mois de janvier', S_LAB)
        r += 1
r += 1

# ---------- F. Cohérence EDEN / FAOSTAT par sous-période
r = title(r, 'F. Cohérence entre les séries principales (EDEN) et alternatives (FAOSTAT), par sous-période',
          "Variations mensuelles en 100 × différence de logarithmes. Résultats figés (script). Un coefficient de variation du rapport proche de zéro signifie que les deux séries sont proportionnelles.")
r = header(r, ['iso3', 'Variable', 'Période', 'Mois', 'Corrélation des variations mensuelles', 'Écart maximal (points)', 'Mois > 2 pts', 'Coefficient de variation du rapport FAOSTAT / EDEN (%)'])
SUB = [('2000-2007', '2000-02', '2007-12'), ('2008-2016', '2008-01', '2016-12'), ('2017-2024', '2017-01', '2024-12'), ('2025-2026', '2025-01', '2026-03')]
for iso in ISO:
    for var in ['cpi_all', 'cpi_food']:
        e = eden[(iso, var)].reindex(M); f = fcp[(iso, var + '_alt')].reindex(M)
        de = 100 * np.log(e).diff(); df = 100 * np.log(f).diff(); dd = df - de; rt = f / e
        for lab, a, z in SUB:
            x = dd.loc[a:z].dropna(); rr_ = rt.loc[a:z].dropna()
            put(ws, f'B{r}', iso, S_LAB); put(ws, f'C{r}', var, S_LAB); put(ws, f'D{r}', lab, S_LAB); put(ws, f'E{r}', int(len(x)), S_PRE, '0')
            put(ws, f'F{r}', round(float(np.corrcoef(de.loc[x.index], df.loc[x.index])[0, 1]), 3), S_PRE, '0.00')
            put(ws, f'G{r}', round(float(x.abs().max()), 2), S_PRE, '0.00'); put(ws, f'H{r}', int((x.abs() > 2).sum()), S_PRE, '0')
            put(ws, f'I{r}', round(float(100 * rr_.std() / rr_.mean()), 2), S_PRE, '0.00')
            r += 1
r += 1

# ---------- G. Ruptures, divergences, valeurs extrêmes (IPC)
r = title(r, 'G. IPC par pays : ruptures, divergences entre sources et valeurs extrêmes',
          "Critères : écart de plus de 2 points entre les variations mensuelles EDEN et FAOSTAT ; variation EDEN à plus de 4 écarts-types robustes ; valeur répétée 4 mois ou plus. Résultats figés (script). Aucune valeur n'a été corrigée.")
r = header(r, ['iso3', 'Variable', 'Date', 'Var. EDEN', 'Variation mensuelle FAOSTAT (100 × Δ ln)', 'Écart (points)', 'Score z', 'Type', 'Critère'])
G_FIRST = r
for _, x in AN.sort_values(['iso3', 'variable', 'date']).iterrows():
    put(ws, f'B{r}', x.iso3, S_LAB); put(ws, f'C{r}', x.variable, S_LAB); put(ws, f'D{r}', x.date, S_LAB)
    put(ws, f'E{r}', num(x.mm_eden), S_PRE, '0.00'); put(ws, f'F{r}', num(x.mm_faostat), S_PRE, '0.00'); put(ws, f'G{r}', num(x.ecart), S_PRE, '0.00')
    put(ws, f'H{r}', num(x.z), S_PRE, '0.0'); put(ws, f'I{r}', x.type, S_LAB); put(ws, f'J{r}', x.crit, S_LAB)
    r += 1
r += 1

# ---------- H. Séries mondiales : valeurs extrêmes
def mm(s): return 100 * np.log(s).diff()


def rz(x):
    x = x.dropna(); med = x.median(); mad = (x - med).abs().median() * 1.4826; return (x - med) / mad


r = title(r, 'H. Séries de l\'onglet Monde : variations mensuelles extrêmes',
          "Variation mensuelle (100 × différence de logarithmes) à plus de 4 écarts-types robustes. Résultats figés (script). Valeurs conservées telles que publiées. gscpi et bceao_import_food non testés.")
r = header(r, ['Date', 'Variable', 'Variation mensuelle', 'Score z'])
for c in monde.columns:
    if c in ('gscpi', 'bceao_import_food'): continue
    d_ = mm(monde[c]); z = rz(d_)
    for dte, zv in z[z.abs() > 4].items():
        put(ws, f'B{r}', dte, S_LAB); put(ws, f'C{r}', c, S_LAB); put(ws, f'D{r}', round(float(d_[dte]), 2), S_PRE, '0.0'); put(ws, f'E{r}', round(float(zv), 1), S_PRE, '0.0')
        r += 1
r += 1

# ---------- I. Production céréalière : bulletin (CILSS) vs FAOSTAT
i0 = next(k for k, l in enumerate(BTXT) if 'Tableau 8.1 Production' in l)
T81 = {}
for l in BTXT[i0:i0 + 30]:
    m = re.match(r'\s*(20\d\d)/20\d\d\s+(.*)$', l)
    if m:
        tok = m.group(2).split(); vals = []; k = 0
        while k < len(tok):
            if re.fullmatch(r'\d{1,3}', tok[k]) and k + 1 < len(tok) and re.fullmatch(r'\d{3},\d', tok[k + 1]): vals.append(float((tok[k] + tok[k + 1]).replace(',', '.'))); k += 2
            else: vals.append(float(tok[k].replace(',', '.'))); k += 1
        assert len(vals) == 9, (l, vals); T81[int(m.group(1))] = vals[:8]
r = title(r, 'I. Production céréalière : Bulletin BCEAO T1 2026 (tableau 8.1, source CILSS) et FAOSTAT (local_agri_supply)',
          "La campagne t/t+1 du bulletin est rapprochée de l'année t de FAOSTAT. Milliers de tonnes. Simple recoupement : seules les valeurs FAOSTAT sont chargées dans Annuel.")
r = header(r, ['iso3', 'Campagne (bulletin)', 'Année FAOSTAT', 'Bulletin', 'FAOSTAT, local_agri_supply (milliers de tonnes)', 'Écart (%)', 'Flag'])
for k, iso in enumerate(ISO):
    for y in range(2020, 2025):
        ra = 3 + YEARS.index(y); cv = L(HA[f'local_agri_supply_{iso}']); cf = L(HA[f'local_agri_supply_flag_{iso}'])
        put(ws, f'B{r}', iso, S_LAB); put(ws, f'C{r}', f'{y}/{y + 1}', S_LAB); put(ws, f'D{r}', str(y), S_LAB)
        put(ws, f'E{r}', T81[y][k], S_PRE, '#,##0.0'); put(ws, f'F{r}', f'=Annuel!${cv}${ra}/1000', S_FORM, '#,##0.0')
        put(ws, f'G{r}', f'=100*(F{r}/E{r}-1)', S_FORM, '0.0'); put(ws, f'H{r}', f'=IF(Annuel!${cf}${ra}="","",Annuel!${cf}${ra})', S_FORM, 'General')
        r += 1

# ---------- J. Audit EDEN / FAOSTAT aux changements de base
AU = pd.read_pickle('audit_final.pkl'); WIN, JAN, ANN = AU['WIN'], AU['JAN'], AU['ANN']
r += 1
r = title(r, 'J. Audit EDEN / FAOSTAT aux changements de base (2008, 2015-2018)',
          "Hors des fenêtres ci-dessous, les deux sources sont la même série (rapport constant à l'arrondi près). Écart de niveau net : positif si EDEN a plus augmenté que FAOSTAT sur la fenêtre. Traitement proposé : à valider, rien n'est appliqué dans le classeur.")
r = header(r, ['iso3', 'Variable', 'Début', 'Fin', 'Variation EDEN au premier mois (100 × Δ ln)', 'Variation FAOSTAT, premier mois', 'Mois', 'Écart de niveau net (points)', 'Corrélation des variations', 'Traitement proposé (à valider)'])
for x in WIN.itertuples():
    put(ws, f'B{r}', x.iso3, S_LAB); put(ws, f'C{r}', x.variable, S_LAB); put(ws, f'D{r}', x.debut, S_LAB); put(ws, f'E{r}', x.fin, S_LAB)
    put(ws, f'F{r}', num(x.mm_eden), S_PRE, '0.00'); put(ws, f'G{r}', num(x.mm_fao), S_PRE, '0.00'); put(ws, f'H{r}', int(x.mois), S_PRE, '0')
    put(ws, f'I{r}', num(x.net), S_PRE, '0.00'); put(ws, f'J{r}', num(x.corr), S_PRE, '0.00'); put(ws, f'K{r}', x.traitement, S_LAB)
    r += 1
r += 1
put(ws, f'B{r}', 'J (suite). Janvier 2008 : variation mensuelle en %, par source', S_LAB_B); r += 1
put(ws, f'B{r}', "Hors alimentation implicite = (indice global FAOSTAT, publié en temps réel, moins poids × alimentation EDEN) / (1 moins poids), avec food_weight de l'onglet Pays (poids de l'étude BCEAO 2023, non ceux de la base 1996). Une valeur très négative signale un saut de l'alimentation incompatible avec l'indice global de l'époque.", S_NOTE); r += 1
r = header(r, ['iso3', 'cpi_all, EDEN', 'cpi_all, FAOSTAT', 'Alim. EDEN', 'cpi_food, FAOSTAT', 'Poids alimentation (%)', 'Hors alim.', 'Lecture'])
for x in JAN.itertuples():
    put(ws, f'B{r}', x.iso3, S_LAB); put(ws, f'C{r}', round(x.all_eden, 2), S_PRE, '0.00'); put(ws, f'D{r}', round(x.all_fao, 2), S_PRE, '0.00')
    put(ws, f'E{r}', round(x.food_eden, 2), S_PRE, '0.00'); put(ws, f'F{r}', round(x.food_fao, 2), S_PRE, '0.00'); put(ws, f'G{r}', x.poids, S_PRE, '0.0')
    put(ws, f'H{r}', round(x.nonfood_rt, 2), S_PRE, '0.00'); put(ws, f'I{r}', x.lecture, S_LAB)
    r += 1
r += 1
put(ws, f'B{r}', 'J (suite). Inflation en moyenne annuelle (%) : chiffres publiés par la BCEAO, EDEN et FAOSTAT', S_LAB_B); r += 1
put(ws, f'B{r}', "BCEAO : Rapport sur l'évolution des prix 2002-2011 (tableau 1), rapports 2016 (annexe 4) et 2017 (tableau 1), relevés automatiquement dans les PDF du site bceao.int le 04/10/2026, à recontrôler avant citation. Le rapport 2017 est encore en base 2008. EDEN et FAOSTAT : formules sur cpi_all et cpi_all_alt.", S_NOTE); r += 1
r = header(r, ['iso3', 'Année', 'BCEAO, publié', 'EDEN', 'FAOSTAT (moyenne annuelle de cpi_all_alt)', 'EDEN moins BCEAO', 'Écart FAO'])
for x in ANN.itertuples():
    r1, r2 = ROW[f'{x.annee}-01'], ROW[f'{x.annee}-12']
    put(ws, f'B{r}', x.iso3, S_LAB); put(ws, f'C{r}', str(x.annee), S_LAB); put(ws, f'D{r}', x.bceao, S_PRE, '0.0')
    put(ws, f'E{r}', f'=100*(AVERAGE({x.iso3}!$B${r1}:$B${r2})/AVERAGE({x.iso3}!$B${r1 - 12}:$B${r2 - 12})-1)', S_FORM, '0.0')
    put(ws, f'F{r}', f'=100*(AVERAGE({x.iso3}!$U${r1}:$U${r2})/AVERAGE({x.iso3}!$U${r1 - 12}:$U${r2 - 12})-1)', S_FORM, '0.0')
    put(ws, f'G{r}', f'=E{r}-D{r}', S_FORM, '0.0'); put(ws, f'H{r}', f'=F{r}-D{r}', S_FORM, '0.0')
    r += 1
CONTROLE_LAST = r - 1
# sommaire des sections
put(ws, f'B{INDEX_ROW}', 'Section', S_HEAD); put(ws, f'C{INDEX_ROW}', 'Ligne de début', S_HEAD)
for col in 'DEFG': sty(ws[f'{col}{INDEX_ROW}'], S_HEAD)
ws[f'D{INDEX_ROW}'].value = 'Intitulé'
for k, (t, rr) in enumerate(sections):
    put(ws, f'B{INDEX_ROW + 1 + k}', t[:1], S_LAB); put(ws, f'C{INDEX_ROW + 1 + k}', rr, S_LAB); put(ws, f'D{INDEX_ROW + 1 + k}', t[3:], S_LAB)
assert INDEX_ROW + 1 + len(sections) < 33

wb.save(OUT)
pd.to_pickle(dict(sections=sections, SUIVI_LAST=SUIVI_LAST, CONTROLE_LAST=CONTROLE_LAST, A_FIRST=A_FIRST, C_FIRST=C_FIRST, C_LAST=C_LAST, T11=T11, T81=T81, n=dict(n_rupt=n_rupt, n_ext=n_ext_c, n_div=n_div_c, exp_cov=exp_cov)), 'build_info.pkl')
print('saved', OUT, 'sections', sections, 'Suivi last', SUIVI_LAST, 'Controle last', CONTROLE_LAST, n_rupt, n_ext_c, n_div_c)
