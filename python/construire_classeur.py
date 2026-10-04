"""Reconstruit le classeur consolidé à partir des fichiers bruts de data/raw.

Usage, depuis la racine du projet :   python python/construire_classeur.py
Prérequis : pandas, numpy, openpyxl, xlrd ; LibreOffice (commande soffice) pour recalculer les formules.

Tout se passe dans _build/ (dossier jetable). En cas de succès, le classeur recalculé et
vérifié est copié dans data/ et la page d'audit dans docs/.
"""
import re, shutil, subprocess, sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PY, RAW, BUILD = RACINE / 'python', RACINE / 'data' / 'raw', RACINE / '_build'
ORIG = '20261002_final_data_project_research_UEMOA.xlsx'
FINAL = '20261004_final_data_project_research_UEMOA_consolidated.xlsx'
ETAPES = ['extract.py',          # lecture et harmonisation des sources            -> all.pkl
          'diag.py',             # recoupements avec le Bulletin BCEAO T1 2026      -> bull_ihpc.pkl
          'flags.py',            # quality_flag, notes, ruptures, valeurs extrêmes  -> flags.pkl
          'audit_fenetres.py',   # fenêtres de divergence EDEN / FAOSTAT            -> audit_windows.pkl
          'audit_officiel.py',   # taux annuels publiés par la BCEAO                -> audit_official.pkl
          'audit_final.py',      # tables de l'audit, données de la page            -> audit_final.pkl, audit_data.json
          'build.py']            # écriture du classeur (formules non calculées)


def lancer(script):
    print(f'--- {script}', flush=True)
    r = subprocess.run([sys.executable, str(PY / script)], cwd=BUILD, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:]); sys.exit(f'Échec : {script}')
    return r.stdout


def soffice():
    for c in ['soffice', 'libreoffice', '/Applications/LibreOffice.app/Contents/MacOS/soffice',
              r'C:\Program Files\LibreOffice\program\soffice.exe']:
        if shutil.which(c) or Path(c).exists(): return shutil.which(c) or c
    sys.exit("LibreOffice introuvable : installer LibreOffice, ou ouvrir _build/" + FINAL + " dans Excel, l'enregistrer, puis lancer python/verify.py depuis _build/.")


def main():
    if BUILD.exists(): shutil.rmtree(BUILD)
    BUILD.mkdir()
    for f in RAW.iterdir():
        if f.is_file(): shutil.copy(f, BUILD / f.name)
    shutil.copy(BUILD / 'Bulletin-Trimestriel-des-Statistiques-mars-2026.txt', BUILD / 'bull.txt')   # pdftotext -layout du PDF
    shutil.copy(RACINE / 'data' / ORIG, BUILD / ORIG)
    for s in ETAPES: lancer(s)
    shutil.copy(BUILD / FINAL, BUILD / 'pre_recalc.xlsx')          # sortie openpyxl, formules sans valeur
    # recalcul des formules par LibreOffice (réécrit le fichier avec les valeurs en cache)
    out = BUILD / 'recalc'; out.mkdir()
    subprocess.run([soffice(), '--headless', '--convert-to', 'xlsx:Calc MS Excel 2007 XML', '--outdir', str(out), str(BUILD / FINAL)],
                   check=True, capture_output=True, timeout=600)
    shutil.copy(out / FINAL, BUILD / FINAL)
    import openpyxl
    wb = openpyxl.load_workbook(BUILD / FINAL, data_only=True)
    err = [(ws.title, c.coordinate, c.value) for ws in wb for row in ws.iter_rows() for c in row
           if isinstance(c.value, str) and re.match(r'^#(REF!|VALUE!|N/A|DIV/0!|NAME\?|NUM!|NULL!)', c.value)]
    vides = wb['Data']['D3'].value is None
    if err or vides: sys.exit(f'Recalcul incorrect : {len(err)} erreurs {err[:5]} ; Data non calculé : {vides}')
    print(lancer('verify.py').split('Tirage aléatoire')[0])
    shutil.copy(BUILD / FINAL, RACINE / 'data' / FINAL)
    page = (PY / 'page_audit_modele.html').read_text(encoding='utf-8').replace('/*DATA*/', (BUILD / 'audit_data.json').read_text(encoding='utf-8'))
    (RACINE / 'docs' / 'audit_eden_faostat.html').write_text(
        '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + page + '</body></html>', encoding='utf-8')
    print('Classeur reconstruit et vérifié :', RACINE / 'data' / FINAL)


if __name__ == '__main__':
    main()
