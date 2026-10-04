# =====================================================================================
# 02_projections_locales.R
# Transmission d'un choc de prix alimentaires mondiaux (indice FAO) à l'inflation dans
# les 8 pays de l'UEMOA : baseline, robustesses, asymétrie, hétérogénéité.
# Prérequis : 01_construire_series.R (sorties/panel_lp.rds).
# =====================================================================================

if (!exists("DOSSIER_SORTIES")) DOSSIER_SORTIES <- "sorties"
if (!exists("DOSSIER_R")) DOSSIER_R <- "R"
source(file.path(DOSSIER_R, "fonctions_lp.R"), encoding = "UTF-8")

# ------------------------------ paramètres ------------------------------------------
H    <- 0:24          # horizons, en mois
P    <- 12            # retards du choc, de l'inflation et des contrôles (choix à valider)
FIN  <- "2024-12"     # dernier mois de l'échantillon principal (IHPC base 2014)
CTRL <- c("d_oil", "d_fx")                 # Brent et USD/XOF, en variation du log

panel <- readRDS(file.path(DOSSIER_SORTIES, "panel_lp.rds"))
prep  <- function(dep, ...) preparer_lp(panel, dep, fin = FIN, P = P, ...)
sortie <- function(nom) file.path(DOSSIER_SORTIES, nom)

# ------------------------------ 1. baseline -----------------------------------------
# cpi_food_main : EDEN, variations FAOSTAT pour la Côte d'Ivoire de 2008-01 à 2010-04
# cpi_all_main  : EDEN, variations FAOSTAT dans cinq fenêtres autour de 2008
base_food <- estimer_lp(prep("cpi_food_main"), H, CTRL, spec = "Baseline (hybride)")
base_all  <- estimer_lp(prep("cpi_all_main"),  H, CTRL, spec = "Baseline (hybride)")
baseline  <- rbind(base_food, base_all)
baseline[, variable := fifelse(dep == "cpi_food_main", "Inflation alimentaire", "Inflation totale")]
# réponse de l'indice FAO à son propre choc, et transmission rapportée à cette réponse
fao <- reponse_du_choc(prep("cpi_food_main"), "fao_food", H, CTRL)
baseline[fao, on = "h", `:=`(reponse_prix_mondial = i.reponse_prix_mondial,
                             transmission_relative = coef / i.reponse_prix_mondial)]
fwrite(baseline, sortie("irf_baseline.csv"), bom = TRUE)
tracer_irf(baseline, sortie("fig_baseline.png"), facette = "variable",
           titre = "Réponse des prix à la consommation à une hausse de 1 % de l'indice FAO",
           sous_titre = "Panel de 8 pays de l'UEMOA, 2000-2024. Bandes à 68 % et 90 %, erreurs-types de Driscoll-Kraay.")

# ------------------------------ 2. robustesses --------------------------------------
# Mali et Niger, cpi_food, janvier 2008 : saut présent dans les deux sources, raccord
# probable. La variation est neutralisée : toute observation dont la fenêtre ou les
# retards contiennent ce mois est exclue pour ces deux pays.
neut <- data.table(iso3 = c("MLI", "NER"), date = "2008-01")

rob_food <- rbind(
  base_food,
  estimer_lp(prep("cpi_food"),      H, CTRL, spec = "EDEN pur"),
  estimer_lp(prep("cpi_food_alt"),  H, CTRL, spec = "FAOSTAT pur"),
  estimer_lp(prep("cpi_food_main", neutraliser = neut), H, CTRL, spec = "Janv. 2008 neutralisé (MLI, NER)"),
  estimer_lp(prep("cpi_food_main", exclure_pays = c("MLI", "NER")), H, CTRL, spec = "Sans Mali ni Niger")
)
rob_all <- rbind(
  base_all,
  estimer_lp(prep("cpi_all"),      H, CTRL, spec = "EDEN pur"),
  estimer_lp(prep("cpi_all_alt"),  H, CTRL, spec = "FAOSTAT pur"),
  estimer_lp(prep("cpi_all_main"), H, c(CTRL, "gscpi"), spec = "Avec GSCPI"),
  estimer_lp(prep("cpi_all_main", exclure_pays = c("MLI", "NER")), H, CTRL, spec = "Sans Mali ni Niger")
)
rob_food[, variable := "Inflation alimentaire"]; rob_all[, variable := "Inflation totale"]
robustesse <- rbind(rob_food, rob_all)
fwrite(robustesse, sortie("irf_robustesse.csv"), bom = TRUE)
tracer_irf(robustesse, sortie("fig_robustesse.png"), couleur = "spec", facette = "variable",
           ruban = "Baseline (hybride)",
           titre = "Robustesse au choix de la série de prix",
           sous_titre = "Réponse à une hausse de 1 % de l'indice FAO. Bande à 90 % de la baseline.", hauteur = 5.5)

# ------------------------------ 3. asymétrie ----------------------------------------
asym <- rbind(
  estimer_lp(prep("cpi_food_main"), H, CTRL, asym = TRUE, spec = "Asymétrie"),
  estimer_lp(prep("cpi_all_main"),  H, CTRL, asym = TRUE, spec = "Asymétrie")
)
asym[, variable := fifelse(dep == "cpi_food_main", "Inflation alimentaire", "Inflation totale")]
asym[, sens := fcase(terme == "choc_pos", "Hausse du prix mondial", terme == "choc_neg", "Baisse du prix mondial",
                     default = "Écart hausse moins baisse")]
fwrite(asym, sortie("irf_asymetrie.csv"), bom = TRUE)
tracer_irf(asym[terme != "hausse_moins_baisse"], sortie("fig_asymetrie.png"), couleur = "sens", facette = "variable",
           titre = "Hausses et baisses de l'indice FAO",
           sous_titre = "Réponse des prix à une variation de 1 % du prix mondial, selon son signe. Bandes à 90 %.", hauteur = 5.5)

# ------------------------------ 4. hétérogénéité ------------------------------------
# Le choc et ses retards sont interagis avec une caractéristique pays centrée. Le
# terme « choc_x » donne le supplément de réponse par unité de la caractéristique.
caracs <- c(food_weight = "Poids de l'alimentation dans le panier (points de %)",
            import_dep_0108 = "Dépendance aux importations céréalières, 2001-2008 (points de %)",
            coastal = "Pays côtier (1) ou enclavé (0)")
hetero <- rbindlist(lapply(names(caracs), function(z) {
  r <- rbind(estimer_lp(prep("cpi_food_main"), H, CTRL, inter = z, spec = z),
             estimer_lp(prep("cpi_all_main"),  H, CTRL, inter = z, spec = z))
  r[, caracteristique := caracs[[z]]]
  r
}))
hetero[, variable := fifelse(dep == "cpi_food_main", "Inflation alimentaire", "Inflation totale")]
fwrite(hetero, sortie("irf_heterogeneite.csv"), bom = TRUE)
tracer_irf(hetero[terme == "choc_x" & dep == "cpi_food_main"], sortie("fig_heterogeneite_food.png"), facette = "caracteristique",
           titre = "Hétérogénéité de la réponse de l'inflation alimentaire",
           sous_titre = "Supplément de réponse par unité de la caractéristique pays. Bandes à 68 % et 90 %.",
           ylab = "Terme d'interaction", echelle_libre = TRUE, largeur = 11, hauteur = 4.5)

# ------------------------------ 5. tableau de synthèse ------------------------------
horizons <- c(0, 3, 6, 12, 18, 24)
synthese <- robustesse[h %in% horizons, .(variable, spec, h, coef = round(coef, 3), se = round(se, 3), nobs, pays)]
synthese_large <- dcast(synthese, variable + spec ~ h, value.var = "coef")
fwrite(synthese, sortie("synthese_robustesse.csv"), bom = TRUE)
cat("\nRéponse cumulée (%) à +1 % de l'indice FAO, par horizon en mois :\n")
print(synthese_large)
cat("\nBaseline : réponse des prix, réponse de l'indice FAO à son propre choc, rapport des deux :\n")
print(baseline[h %in% horizons, .(variable, h, reponse = round(coef, 3), se = round(se, 3),
                                  indice_fao = round(reponse_prix_mondial, 2),
                                  transmission_relative = round(transmission_relative, 3), nobs, pays)])
