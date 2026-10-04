# Journal méthodologique

État au 4 octobre 2026. Ce document reprend, dans l'ordre, ce qui a été fait et décidé. Les chiffres
viennent du classeur consolidé et des sorties de R ; ils se régénèrent avec les deux commandes de
`CLAUDE.md`.

## 1. Base de données

### Sources et variables

| Variable | Source | Fichier brut | Couverture dans le gabarit |
|---|---|---|---|
| `cpi_all`, `cpi_food` | BCEAO EDEN, base 100 = 2023 | `exportIndicateurs_1.csv` | 2000-01 à 2026-05 ; `cpi_food` GNB depuis 2002-07 |
| `cpi_all_umoa`, `cpi_food_umoa` | BCEAO EDEN, agrégat | `exportIndicateurs.csv` | 2000-01 à 2026-05 (onglet Monde, hors Data) |
| `cpi_all_alt`, `cpi_food_alt` | FAOSTAT CP, 2015 = 100 | `FAOSTAT_data_en_10-4-2026.csv` | 2000-01 à 2026-03 |
| `fao_food` et sous-indices | FAO Food Price Index, nominal | `food_price_indices_data.csv` | 2000-01 à 2026-09 |
| `oil_usd`, `rice_thai`, `wheat_hrw`, `palm_oil`, `sugar_world`, `maize` | Banque mondiale, Pink Sheet | `CMO-Historical-Data-Monthly.xlsx` | 2000-01 à 2026-09 |
| `eur_usd` | BCE, EXR.M.USD.EUR.SP00.A | `ECB_Data_Portal_20261004111939.csv` | 2000-01 à 2026-09 |
| `usd_xof` | formule 655,957 / `eur_usd` | | 2000-01 à 2026-09 |
| `gscpi` | Fed de New York | `gscpi_data.xlsx` | 2000-01 à 2026-08 |
| `bceao_import_food` | Bulletin BCEAO T1 2026, tableau 9.5 | PDF, page 31 | 2024-10 à 2026-03 |
| `import_food_idx` | formule, poids de l'onglet Parametres | | 2000-01 à 2026-09 |
| `local_agri_supply` | FAOSTAT QCL, « Cereals, primary », Production | `FAOSTAT_data_en_10-4-2026_2.csv` | 2000 à 2024 |
| `import_dependency` | FAOSTAT FS, moyenne sur 3 ans, année centrale | `FAOSTAT_data_en_10-4-2026_1.csv` | inégale selon le pays |
| `food_imports_share` | Banque mondiale, TM.VAL.FOOD.ZS.UN | `API_TM.VAL.FOOD.ZS.UN_DS2_...csv` | 2000 à 2024, avec trous |

Fichiers reçus mais non utilisés : trois extraits FAOSTAT partiels ou redondants
(`Consumer_price_indices_...FAOSTAT.csv`, `..._1.csv`, `result.csv`), identiques au fichier de
référence sur leur périmètre, et `gscpi_data.xls`, identique au `.xlsx`.

### Conventions

- Séries en niveau, dans l'unité de la source. Dates en texte AAAA-MM. Manquant = cellule vide.
- Aucune interpolation ni extrapolation. Valeur annuelle répétée sur les 12 mois dans `Data`.
- `Data` : 2 568 lignes (8 pays x 321 mois), sans doublon. Sur l'échantillon principal
  (jusqu'à 2024-12), 300 mois par pays, sauf `cpi_food` en Guinée-Bissau (270).

### Contrôles faits

- 17 019 valeurs du classeur relues dans les fichiers bruts par un second programme : aucun écart.
- 124 100 formules d'origine conservées à l'identique ; aucune erreur de formule après recalcul.
- `usd_xof` calculé coïncide avec le tableau 9.3 du Bulletin BCEAO T1 2026.
- EDEN coïncide avec les tableaux 11.1.x.a du Bulletin T1 2026 sur 156 mois-pays sur 168 ; les
  12 écarts sont au Mali (2025-01, 2025-03 à 2025-09), au Niger (2025-03 à 2025-05) et au Burkina Faso (2026-01).

## 2. Audit EDEN / FAOSTAT

Question : EDEN présente des sauts mensuels aux changements de base de l'IHPC (2008-01, 2017-01).
Quelle série d'inflation utiliser en baseline ?

### Constats

1. **Même série hors fenêtres.** Le rapport FAOSTAT / EDEN est constant à l'arrondi près, sauf dans
   des fenêtres de un à deux ans après chaque changement de base : 2008-2009 dans sept pays, 2017-2018
   (BEN, CIV, MLI, SEN), 2015-2016 (BFA, NER, TGO), 2020-2022 (GNB, TGO).
2. **Janvier 2008 est un raccord dans `cpi_all` d'EDEN.** Variation du mois : CIV 6,3 % (FAOSTAT 1,6 %),
   MLI 4,7 % (0,6 %), NER 3,7 % (-0,1 %). En Côte d'Ivoire, le glissement annuel d'EDEN passe de 1,5 %
   à 6,7 % en un mois, reste entre 5,0 % et 7,1 % toute l'année, retombe à 1,5 % en janvier 2009 ;
   celui de FAOSTAT monte de 2,1 % à 9,7 % en septembre. Hausse cumulée de décembre 2007 à
   décembre 2009 : 7,0 % et 7,2 %. EDEN respecte la moyenne annuelle, pas le calendrier.
3. **Une indicatrice ne suffit pas** : elle retire le saut mais laisse un profil trop plat ensuite.
4. **`cpi_food` : pas de contre-source dans quatre pays.** FAOSTAT reprend EDEN au Bénin, au Burkina
   Faso, au Mali et presque au Niger. Saut de janvier 2008 : BFA 7,2 %, BEN 6,1 %, NER 5,7 %, MLI 4,0 %.
   Au Mali et au Niger il supposerait un recul de plus de 4 % du reste du panier (indice global de
   l'époque : +0,6 % et -0,1 %) : raccord probable. Au Burkina Faso et au Bénin l'indice global monte
   aussi (2,7 % et 1,4 %) : hausse au moins en partie réelle.
5. **Taux annuels publiés par la BCEAO.** Sur 112 pays-années (2002-2011, 2014-2017), EDEN reproduit
   le chiffre publié à 0,15 point près dans 89 cas, FAOSTAT dans 90. EDEN est exact en 2015-2016 là où
   FAOSTAT s'écarte de 1,6 point au Niger ; FAOSTAT reproduit les taux 2017 publiés en base 2008
   (BEN, CIV, MLI, SEN) là où EDEN porte vraisemblablement la série recalculée en base 2014.
6. La BCEAO situait le pic de l'Union à 10,8 % en août 2008 ; l'agrégat EDEN donne 9,0 % ce mois-là.

### Décision (validée par l'auteur le 04/10/2026)

Série hybride : EDEN par défaut, variations mensuelles FAOSTAT dans six fenêtres.

| Série | Fenêtre | Motif |
|---|---|---|
| CIV, `cpi_all` | 2008-01 à 2009-11 | Saut de raccord : 6,3 % contre 1,6 % |
| MLI, `cpi_all` | 2008-01 à 2009-07 | Saut de raccord : 4,7 % contre 0,6 % |
| NER, `cpi_all` | 2008-01 à 2009-04 | Saut de raccord : 3,7 % contre -0,1 % ; taux 2008 publié 11,3 %, EDEN 10,5 % |
| GNB, `cpi_all` | 2008-01 à 2010-03 | Taux 2008 publié 10,4 % : EDEN 7,3 %, FAOSTAT 10,5 % |
| SEN, `cpi_all` | 2007-08 à 2010-01 | Creux isolé d'EDEN en 2007-08 (-5,1 % puis +7,0 %) ; taux 2009 et 2010 publiés reproduits par FAOSTAT seul |
| CIV, `cpi_food` | 2008-01 à 2010-04 | Saut de raccord : 10,3 % contre 2,1 % |

Règle : une fenêtre est retenue si le premier mois d'EDEN est un saut de raccord (écart de plus de
2 points avec FAOSTAT et même hausse cumulée en fin de fenêtre), ou si EDEN s'écarte du taux annuel
publié par la BCEAO alors que FAOSTAT le reproduit. La substitution est fixée avant toute estimation.

Points assumés :
- aucune substitution en 2015-2018 ;
- `cpi_food` au Mali et au Niger en janvier 2008 : donnée publiée conservée en baseline, robustesses dédiées ;
- pas de recherche de bulletins nationaux de 2008 pour le mémoire ;
- Sénégal `cpi_food` : même creux isolé en 2007-08 dans EDEN (-6,3 % puis +10,0 %), mais les deux
  sources ne cumulent pas la même hausse sur la fenêtre : pas de substitution.

Détail chiffré : onglet `Controle`, section J, et `docs/audit_eden_faostat.html`.

## 3. Construction des séries dans R

`R/01_construire_series.R` : variation mensuelle du log égale à celle de FAOSTAT dans la fenêtre et à
celle d'EDEN ailleurs, puis chaînage à rebours depuis la dernière observation EDEN.

| Série | Mois substitués | Hausse cumulée EDEN | Hausse cumulée hybride | Facteur avant la fenêtre |
|---|---|---|---|---|
| CIV `cpi_all` | 23 | 6,55 % | 6,55 % | 1,0000 |
| MLI `cpi_all` | 19 | 12,98 % | 12,91 % | 1,0007 |
| NER `cpi_all` | 16 | 5,62 % | 5,67 % | 0,9996 |
| GNB `cpi_all` | 27 | 1,26 % | 5,15 % | 0,9630 |
| SEN `cpi_all` | 30 | 3,06 % | 4,58 % | 0,9855 |
| CIV `cpi_food` | 28 | 24,57 % | 24,39 % | 1,0015 |

Le script s'arrête si l'hybride diffère d'EDEN hors fenêtre, ou si huit valeurs de référence
calculées indépendamment ne sont pas retrouvées.

## 4. Premiers résultats (exécution du 04/10/2026)

Réponse cumulée des prix, en %, à une hausse de 1 % de l'indice FAO ; erreurs-types de Driscoll-Kraay.

| Variable | Spécification | h = 6 | h = 12 | h = 24 |
|---|---|---|---|---|
| Alimentation | Baseline (hybride) | 0,165 | 0,349 | 0,618 |
| Alimentation | EDEN pur | 0,167 | 0,342 | 0,609 |
| Alimentation | FAOSTAT pur | 0,199 | 0,366 | 0,623 |
| Alimentation | Janvier 2008 neutralisé (MLI, NER) | 0,147 | 0,339 | 0,605 |
| Alimentation | Sans Mali ni Niger | 0,172 | 0,378 | 0,607 |
| Total | Baseline (hybride) | 0,097 | 0,237 | 0,383 |
| Total | EDEN pur | 0,102 | 0,206 | 0,345 |
| Total | FAOSTAT pur | 0,105 | 0,238 | 0,377 |
| Total | Avec GSCPI | 0,106 | 0,260 | 0,346 |
| Total | Sans Mali ni Niger | 0,100 | 0,247 | 0,382 |

- **Lecture.** L'indice FAO répond à son propre choc : +2,49 % à 6 mois, +2,37 % à 12 mois, +1,45 % à
  24 mois. Rapportée à cette réponse, la transmission est de 0,15 puis 0,43 pour l'alimentation et de
  0,10 puis 0,26 pour l'inflation totale.
- **Robustesse.** Le choix de série pèse peu sur la moyenne du panel.
- **Asymétrie.** Alimentation à 24 mois : 0,98 pour une hausse, 0,23 pour une baisse (écart 0,75,
  erreur-type 0,30). Inflation totale : 0,46 et 0,32, écart non significatif.
- **Hétérogénéité.** Les pays côtiers répondent moins à long horizon (terme d'interaction de l'ordre
  de -0,2 à 24 mois). Poids alimentaire et dépendance céréalière : non significatifs.

Ces résultats sont un premier passage. Ils dépendent de choix non encore validés par l'auteur
(12 retards, effets fixes pays et mois calendaire, h + 1 retards de Driscoll-Kraay).

## 5. Sources externes consultées pour l'audit

- BCEAO, Rapport sur l'évolution des prix à la consommation dans l'UEMOA, 2002-2011 (tableau 1, pic d'août 2008) :
  https://www.bceao.int/sites/default/files/2017-12/Rapport_sur_l_evolution_des_prix_a_la_consommation_dans_l_UEMOA_sur_les_dix_dernieres_annees_(2002_2011).pdf
- BCEAO, Rapport sur l'évolution des prix en 2016 (annexe 4) :
  https://www.bceao.int/sites/default/files/2017-11/rapport_sur_l_evolution_des_prix_a_la_consommation_dans_l_uemoa_en_2016_et_perspectives.pdf
- BCEAO, Rapport sur l'évolution des prix en 2017 (tableau 1, indices en base 2008) :
  https://www.bceao.int/sites/default/files/2018-04/Rapport%20sur%20l'%C3%A9volution%20des%20prix%20%C3%A0%20la%20consommation%20dans%20l'UEMOA%20en%202017%20et%20perspectives.pdf

Les chiffres tirés de ces rapports ont été relevés automatiquement dans les PDF : à recontrôler avant citation.
