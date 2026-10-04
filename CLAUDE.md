# Transmission des prix alimentaires mondiaux à l'inflation dans l'UEMOA

Mémoire de Mastère Spécialisé ENSAE : « Transmission d'un choc de prix des matières premières à
l'indice des prix à la consommation : application aux pays de l'UEMOA ». Panel mensuel de 8 pays
(BEN, BFA, CIV, GNB, MLI, NER, SEN, TGO), 2000-01 à 2026-09, estimé par projections locales.

L'auteur travaille en français : répondre, commenter le code et nommer les sorties en français.

## État au 04/10/2026

- Collecte terminée, base maître consolidée et vérifiée (classeur Excel, 17 onglets).
- Audit EDEN / FAOSTAT fait, série de base décidée (hybride à six fenêtres, voir plus bas).
- Chaîne R écrite et testée : construction des séries, baseline, robustesses, asymétrie, hétérogénéité.
- Reste : choix de présentation, extensions, rédaction (section « Suite du travail »).

Le détail des décisions, de l'audit et des résultats est dans `docs/methodologie.md`.
Le cahier des charges d'origine est dans `docs/cahier_des_charges_initial.txt`.

## Arborescence

- `data/20261004_final_data_project_research_UEMOA_consolidated.xlsx` : base maître. L'onglet `Data`
  est le panel long lu par R (en-tête en ligne 2). `Lisez-moi`, `Source`, `Suivi`, `Controle`
  documentent sources, couverture et contrôles (audit en `Controle`, section J).
- `data/20261002_final_data_project_research_UEMOA.xlsx` : classeur d'origine, à ne jamais modifier.
- `data/raw/` : fichiers bruts tels que téléchargés (BCEAO EDEN, FAOSTAT, FAO, Pink Sheet, BCE,
  Fed de New York, WDI, Bulletin BCEAO T1 2026 en PDF et en texte).
- `R/` : chaîne d'estimation. `python/` : reconstruction du classeur à partir de `data/raw/`.
- `sorties/` : résultats de la dernière exécution de R (CSV, PNG, `panel_lp.rds`).
- `docs/audit_eden_faostat.html` : page d'audit avec graphiques, à ouvrir dans un navigateur.

## Commandes

Toutes se lancent depuis la racine du projet.

```bash
Rscript R/00_lancer.R                    # séries hybrides puis toutes les projections locales (15 s)
python python/construire_classeur.py     # reconstruit et vérifie le classeur depuis data/raw (35 s)
```

- R : packages `readxl`, `data.table`, `fixest`, `ggplot2`. Testé avec R 4.3.3 et fixest 0.14.2.
  Scripts en UTF-8 ; sous Windows, lancer R avec une locale UTF-8 pour les accents des figures.
- Python : `pandas`, `numpy`, `openpyxl`, `xlrd`, plus LibreOffice (`soffice`) pour recalculer les
  formules. Le script travaille dans `_build/` (jetable) et ne remplace le classeur qu'après
  vérification : 17 019 valeurs relues dans les fichiers bruts, aucun écart toléré.

## Règles de travail

- Aucune correction manuelle dans Excel. Le classeur garde les séries sources en niveau ; toute
  transformation (logs, variations, retards, séries hybrides) se fait dans R et doit être reproductible.
- Ne jamais remplacer un manquant par zéro, ni interpoler, ni extrapoler.
- En cas de conflit entre sources, garder les deux séries. Ne pas rebaser ni raccorder dans Excel.
- Ne pas modifier le classeur à la main : changer `python/build.py` puis relancer
  `python/construire_classeur.py`. Les formules d'origine du classeur doivent rester intactes
  (`python/verify.py` le contrôle).
- Toute substitution de série se justifie par un problème de mesure identifié avant estimation,
  jamais par les résultats des projections locales.
- Les chiffres BCEAO de `Controle` section J viennent d'une lecture automatique de PDF : les
  recontrôler sur les rapports avant de les citer dans le mémoire.

## Décisions méthodologiques figées

1. **Inflation totale : série hybride `cpi_all_main`.** EDEN partout, sauf dans cinq fenêtres où la
   variation mensuelle est celle de FAOSTAT : CIV 2008-01 à 2009-11, MLI 2008-01 à 2009-07,
   NER 2008-01 à 2009-04, GNB 2008-01 à 2010-03, SEN 2007-08 à 2010-01.
2. **Inflation alimentaire : `cpi_food_main`.** EDEN partout, sauf CIV 2008-01 à 2010-04 (seul pays
   avec une vraie contre-source alimentaire).
3. **Chaînage.** Variations mensuelles chaînées à rebours depuis la dernière observation EDEN :
   l'hybride vaut exactement EDEN après la fenêtre, EDEN multiplié par une constante avant.
4. **Aucune substitution en 2015-2018** : écarts de versions officielles, enjeu faible.
5. **`cpi_food` au Mali et au Niger, janvier 2008** : saut présent dans les deux sources, raccord
   probable. Donnée conservée telle quelle en baseline, traitée en robustesse seulement.
6. **Guinée-Bissau avant 2002-07** : exclue de toutes les variantes (EDEN rétropolé sur la Côte
   d'Ivoire, `cpi_food` absent, FAOSTAT imputé).
7. **Échantillon principal** arrêté à 2024-12 (passage à l'IHPC base 2023 en 2025-01).
8. **Robustesses retenues** : EDEN pur, FAOSTAT pur, janvier 2008 neutralisé pour MLI et NER,
   estimation sans MLI ni NER, ajout du GSCPI.

La règle et les motifs par fenêtre sont dans `R/01_construire_series.R` et `sorties/annexe_fenetres.csv`
(tableau destiné à l'annexe du mémoire).

## Spécification des projections locales

Pour chaque horizon h de 0 à 24 :
`y[i,t+h] - y[i,t-1] = a_i + m_mois + b_h choc[t] + retards du choc + retards de l'inflation + contrôles`,
avec y = 100 log(indice) et choc = variation de 100 log(`fao_food`).

- 12 retards du choc, de l'inflation et des contrôles (choix de l'assistant, à valider).
- Contrôles : Brent (`oil_usd`) et `usd_xof` en variation du log, retards 0 à 12. GSCPI en robustesse.
- Effets fixes pays et mois calendaire. Erreurs-types de Driscoll-Kraay avec h + 1 retards.
- Le choc est commun aux pays : l'identification vient de la dimension temporelle.
- Asymétrie : hausses et baisses du prix mondial séparées. Hétérogénéité : interaction du choc avec
  `food_weight`, la dépendance céréalière moyenne 2001-2008 (`import_dep_0108`) et `coastal`.

## Pièges de données

- `Data` est alimenté par formules : lire avec `readxl::read_excel(..., sheet = "Data", skip = 1, na = "")`.
- `cpi_all`, `cpi_food` (EDEN) sont en base 100 = 2023 ; `cpi_all_alt`, `cpi_food_alt` (FAOSTAT) en
  base 2015 = 100. Comparer des variations, jamais des niveaux.
- Hors des fenêtres de divergence, EDEN et FAOSTAT sont la même série. Pour `cpi_food`, FAOSTAT
  reprend EDEN au Bénin, au Burkina Faso, au Mali et presque au Niger : ce n'est pas une source indépendante.
- `quality_flag` : flags FAOSTAT « général|alimentaire » puis codes séparés par « ; »
  (`DIV_ALL`, `DIV_FOOD`, `EDEN_RETRO`, `EDEN_RUPTURE`, `EDEN_PLATEAU`, `BULL_DIFF`), définis dans `Lisez-moi`.
- `import_food_idx` est un indice synthétique sans unité, sans taux de change. Une variante en FCFA
  se construit dans R avec `usd_xof`.
- `bceao_import_food` n'a que 18 mois (2024-10 à 2026-03). `rain_anom` et `gdp_real` sont vides.
- `import_dependency` ne couvre que 2001-2008 pour BEN, MLI, TGO ; d'où la moyenne 2001-2008.
- Dans les formules Excel, écrire `BEN!$B$3:$B$14` et non `BEN!$B$3:BEN!$B$14` : les noms d'onglets
  pays sont aussi des noms de colonnes valides et LibreOffice interprète mal la seconde forme.

## Résultats de référence

Une réexécution de `Rscript R/00_lancer.R` doit redonner, pour +1 % de l'indice FAO :

| | h = 6 | h = 12 | h = 24 |
|---|---|---|---|
| `cpi_food_main` | 0,165 | 0,349 (e.-t. 0,112) | 0,618 (e.-t. 0,130) |
| `cpi_all_main` | 0,097 | 0,237 (e.-t. 0,069) | 0,383 (e.-t. 0,078) |

2 266 observations à h = 0, 2 074 à h = 24, 8 pays. L'indice FAO répond lui-même à son choc
(+2,37 % à 12 mois, +1,45 % à 24 mois) : `irf_baseline.csv` donne aussi la transmission rapportée
à cette réponse (0,147 et 0,425 pour l'alimentation).

## Suite du travail

À décider par l'auteur :
- lecture mise en avant dans le mémoire : réponse brute ou transmission rapportée à la réponse de l'indice FAO ;
- nombre de retards (12 par défaut) et effets fixes mois par pays (`ef = "iso3^mois"`) en sensibilité.

Extensions prévues dans `Lisez-moi`, non encore codées : estimation pays par pays, choc en FCFA,
chocs par produit (`rice_thai`, `wheat_hrw`, `fao_cereals`...), `import_food_idx` comme choc,
rupture en 2020, interaction avec `import_share_cpi`. `preparer_lp()` accepte déjà `choc_var`.

Rédaction : règle de substitution et tableau des six fenêtres en annexe, section de robustesse,
mention explicite du saut de janvier 2008 au Mali et au Niger.
