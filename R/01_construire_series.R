# =====================================================================================
# 01_construire_series.R
# Lit l'onglet Data du classeur consolidé et construit, sans aucune correction manuelle :
#   cpi_all_main  : EDEN, avec les variations mensuelles FAOSTAT dans cinq fenêtres
#   cpi_food_main : EDEN, avec les variations mensuelles FAOSTAT dans une fenêtre (CIV)
# Les variantes de robustesse (EDEN pur, FAOSTAT pur) sont les colonnes d'origine.
# Sorties : sorties/panel_lp.rds, sorties/annexe_fenetres.csv, sorties/controle_hybride.csv
# =====================================================================================

suppressPackageStartupMessages({
  library(readxl)
  library(data.table)
})

if (!exists("FICHIER_XLSX")) FICHIER_XLSX <- "data/20261004_final_data_project_research_UEMOA_consolidated.xlsx"
if (!exists("DOSSIER_SORTIES")) DOSSIER_SORTIES <- "sorties"
dir.create(DOSSIER_SORTIES, showWarnings = FALSE)

# ---------------------------------------------------------------------------------
# 1. Lecture du panel (en-tête en ligne 2 ; cellule vide = valeur manquante)
# ---------------------------------------------------------------------------------
panel <- as.data.table(read_excel(FICHIER_XLSX, sheet = "Data", skip = 1, na = ""))
setnames(panel, "Date", "date")
setkey(panel, iso3, date)

stopifnot(
  nrow(panel) == 2568,                              # 8 pays x 321 mois
  uniqueN(panel$iso3) == 8,
  !anyDuplicated(panel[, .(iso3, date)]),
  is.numeric(panel$cpi_all), is.numeric(panel$cpi_food),
  is.numeric(panel$cpi_all_alt), is.numeric(panel$cpi_food_alt)
)

# indice de temps mensuel : 1 = 2000-01
panel[, t := (as.integer(substr(date, 1, 4)) - 2000L) * 12L + as.integer(substr(date, 6, 7))]
panel[, mois := as.integer(substr(date, 6, 7))]
stopifnot(panel[, all(diff(t) == 1L), by = iso3]$V1)   # mois consécutifs dans chaque pays

# ---------------------------------------------------------------------------------
# 2. Fenêtres de substitution (audit du 04/10/2026, onglet Controle, section J)
#    Règle : EDEN par défaut ; dans une fenêtre, la variation mensuelle retenue est
#    celle de FAOSTAT. Une fenêtre est retenue si le premier mois d'EDEN est un saut
#    de raccord (écart de plus de 2 points avec FAOSTAT, même hausse cumulée en fin
#    de fenêtre), ou si EDEN s'écarte du taux annuel publié par la BCEAO alors que
#    FAOSTAT le reproduit. Aucune substitution en 2015-2018.
# ---------------------------------------------------------------------------------
fenetres <- data.table(
  iso3     = c("CIV", "MLI", "NER", "GNB", "SEN", "CIV"),
  variable = c("cpi_all", "cpi_all", "cpi_all", "cpi_all", "cpi_all", "cpi_food"),
  debut    = c("2008-01", "2008-01", "2008-01", "2008-01", "2007-08", "2008-01"),
  fin      = c("2009-11", "2009-07", "2009-04", "2010-03", "2010-01", "2010-04"),
  motif    = c(
    "Saut de raccord en 2008-01 : +6,3 % dans EDEN, +1,6 % dans FAOSTAT",
    "Saut de raccord en 2008-01 : +4,7 % dans EDEN, +0,6 % dans FAOSTAT",
    "Saut de raccord en 2008-01 : +3,7 % dans EDEN, -0,1 % dans FAOSTAT ; taux 2008 publié 11,3 %, EDEN 10,5 %",
    "Taux 2008 publié par la BCEAO 10,4 % : EDEN 7,3 %, FAOSTAT 10,5 %",
    "Creux isolé d'EDEN en 2007-08 (-5,1 % puis +7,0 %) ; taux 2009 et 2010 publiés reproduits par FAOSTAT seul",
    "Saut de raccord en 2008-01 : +10,3 % dans EDEN, +2,1 % dans FAOSTAT"
  )
)

# ---------------------------------------------------------------------------------
# 3. Construction de la série hybride
#    g_t = variation mensuelle du log : FAOSTAT dans la fenêtre, EDEN ailleurs.
#    Le niveau est obtenu par chaînage arrière depuis la dernière observation EDEN :
#    la série coïncide donc avec EDEN après la dernière fenêtre (base 100 = 2023
#    conservée) et l'indice reste continu ; avant la fenêtre, EDEN est multiplié par
#    une constante.
# ---------------------------------------------------------------------------------
construire_hybride <- function(dt, var_eden, var_fao, fen) {
  x <- copy(dt[, .(iso3, date, t, e = get(var_eden), f = get(var_fao))])
  setkey(x, iso3, t)
  x[, g_e := log(e) - shift(log(e)), by = iso3]
  x[, g_f := log(f) - shift(log(f)), by = iso3]
  x[, `:=`(g = g_e, source = "EDEN")]
  for (k in seq_len(nrow(fen))) {
    sel <- x$iso3 == fen$iso3[k] & x$date >= fen$debut[k] & x$date <= fen$fin[k]
    if (anyNA(x$g_f[sel])) stop("FAOSTAT manquant dans la fenêtre ", fen$iso3[k], " ", fen$debut[k])
    x[sel, `:=`(g = g_f, source = "FAOSTAT")]
  }
  x[, hybride := {
    dernier <- max(which(!is.na(e)))                 # dernière observation EDEN
    cs <- cumsum(fifelse(is.na(g), 0, g))
    niveau <- exp(log(e[dernier]) - (cs[dernier] - cs))
    niveau[is.na(e)] <- NA_real_                     # pas de valeur là où EDEN est absent
    niveau
  }, by = iso3]
  x[, .(iso3, date, hybride, source)]
}

h_all  <- construire_hybride(panel, "cpi_all",  "cpi_all_alt",  fenetres[variable == "cpi_all"])
h_food <- construire_hybride(panel, "cpi_food", "cpi_food_alt", fenetres[variable == "cpi_food"])
panel[h_all,  on = .(iso3, date), `:=`(cpi_all_main  = i.hybride, src_all_main  = i.source)]
panel[h_food, on = .(iso3, date), `:=`(cpi_food_main = i.hybride, src_food_main = i.source)]

# ---------------------------------------------------------------------------------
# 4. Contrôles de la construction
# ---------------------------------------------------------------------------------
# (a) hors fenêtre, la variation mensuelle est exactement celle d'EDEN
verif <- function(main, eden, src) {
  d <- panel[, .(iso3, date, g_m = log(get(main)) - shift(log(get(main))),
                 g_e = log(get(eden)) - shift(log(get(eden))), s = get(src)), by = .(pays = iso3)]
  stopifnot(d[s == "EDEN" & !is.na(g_e), max(abs(g_m - g_e))] < 1e-10)
}
verif("cpi_all_main", "cpi_all", "src_all_main")
verif("cpi_food_main", "cpi_food", "src_food_main")

# (b) après la dernière fenêtre du pays, le niveau est exactement celui d'EDEN
for (k in seq_len(nrow(fenetres))) {
  v <- fenetres$variable[k]; m <- paste0(v, "_main")
  fin_max <- fenetres[iso3 == fenetres$iso3[k] & variable == v, max(fin)]
  d <- panel[iso3 == fenetres$iso3[k] & date > fin_max & !is.na(get(v))]
  stopifnot(max(abs(d[[m]] - d[[v]])) < 1e-9)
}

# (c) pays sans fenêtre : série identique à EDEN
sans_fen_all  <- setdiff(unique(panel$iso3), fenetres[variable == "cpi_all", iso3])
sans_fen_food <- setdiff(unique(panel$iso3), fenetres[variable == "cpi_food", iso3])
stopifnot(panel[iso3 %in% sans_fen_all  & !is.na(cpi_all),  max(abs(cpi_all_main  - cpi_all))]  < 1e-9)
stopifnot(panel[iso3 %in% sans_fen_food & !is.na(cpi_food), max(abs(cpi_food_main - cpi_food))] < 1e-9)

# (d) valeurs de référence, calculées indépendamment (Python) le 04/10/2026
ref <- data.table(
  iso3 = c("CIV", "CIV", "MLI", "NER", "GNB", "SEN", "CIV", "CIV"),
  date = c("2007-12", "2008-01", "2008-01", "2008-09", "2007-12", "2008-01", "2007-12", "2008-09"),
  var  = c(rep("cpi_all_main", 6), rep("cpi_food_main", 2)),
  val  = c(68.702299, 69.807161, 70.559679, 84.411163, 68.948041, 72.523518, 52.577075, 61.114236)
)
for (k in seq_len(nrow(ref))) {
  obtenu <- panel[iso3 == ref$iso3[k] & date == ref$date[k]][[ref$var[k]]]
  if (abs(obtenu - ref$val[k]) > 1e-5) stop("Valeur de référence non retrouvée : ", ref$iso3[k], " ", ref$date[k], " ", ref$var[k])
}

# (e) Guinée-Bissau avant 2002-07 : cpi_all d'EDEN est une rétropolation, cpi_food est
#     absent. Ces mois sont exclus de toutes les variantes (y compris FAOSTAT, imputé).
panel[, exclu_gnb := iso3 == "GNB" & date < "2002-07"]

# ---------------------------------------------------------------------------------
# 5. Caractéristiques structurelles pour les interactions
#    import_dependency : moyenne 2001-2008, seule fenêtre commune aux 8 pays.
# ---------------------------------------------------------------------------------
dep <- panel[date >= "2001-01" & date <= "2008-12", .(import_dep_0108 = mean(import_dependency, na.rm = TRUE)), by = iso3]
stopifnot(nrow(dep) == 8, !anyNA(dep$import_dep_0108))
panel[dep, on = "iso3", import_dep_0108 := i.import_dep_0108]

# ---------------------------------------------------------------------------------
# 6. Sorties
# ---------------------------------------------------------------------------------
saveRDS(panel, file.path(DOSSIER_SORTIES, "panel_lp.rds"))
fwrite(fenetres, file.path(DOSSIER_SORTIES, "annexe_fenetres.csv"), bom = TRUE)

controle <- rbindlist(lapply(seq_len(nrow(fenetres)), function(k) {
  v <- fenetres$variable[k]; m <- paste0(v, "_main"); i <- fenetres$iso3[k]
  mois_avant <- panel[iso3 == i & date < fenetres$debut[k], max(date)]
  d <- panel[iso3 == i]
  data.table(
    iso3 = i, variable = v, debut = fenetres$debut[k], fin = fenetres$fin[k],
    mois = d[date >= fenetres$debut[k] & date <= fenetres$fin[k], .N],
    hausse_cumulee_eden_pct    = 100 * (d[date == fenetres$fin[k]][[v]] / d[date == mois_avant][[v]] - 1),
    hausse_cumulee_hybride_pct = 100 * (d[date == fenetres$fin[k]][[m]] / d[date == mois_avant][[m]] - 1),
    facteur_avant_fenetre      = d[date == mois_avant][[m]] / d[date == mois_avant][[v]]
  )
}))
fwrite(controle, file.path(DOSSIER_SORTIES, "controle_hybride.csv"), bom = TRUE)

cat("Séries construites :", nrow(panel), "lignes ;",
    panel[src_all_main == "FAOSTAT", .N], "mois-pays substitués pour cpi_all,",
    panel[src_food_main == "FAOSTAT", .N], "pour cpi_food.\n")
print(controle)
