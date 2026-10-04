# =====================================================================================
# 00_lancer.R : exécute toute la chaîne depuis le classeur Excel.
#
# Mode d'emploi
#   1. Installer une fois les packages :
#        install.packages(c("readxl", "data.table", "fixest", "ggplot2"))
#   2. Depuis la racine du projet : Rscript R/00_lancer.R
#      (ou source("R/00_lancer.R", encoding = "UTF-8")). Les scripts sont en UTF-8.
#
# Tout est reconstruit à partir de l'onglet Data ; rien n'est corrigé à la main.
# Résultats dans le dossier « sorties » :
#   annexe_fenetres.csv       les six fenêtres de substitution (annexe du mémoire)
#   controle_hybride.csv      hausse cumulée EDEN et hybride sur chaque fenêtre
#   panel_lp.rds              panel avec cpi_all_main et cpi_food_main
#   irf_*.csv, fig_*.png      réponses estimées et graphiques
#   synthese_robustesse.csv   réponses aux horizons 0, 3, 6, 12, 18 et 24 mois
# =====================================================================================

FICHIER_XLSX    <- "data/20261004_final_data_project_research_UEMOA_consolidated.xlsx"
DOSSIER_SORTIES <- "sorties"
DOSSIER_R       <- "R"

source(file.path(DOSSIER_R, "01_construire_series.R"), encoding = "UTF-8")
source(file.path(DOSSIER_R, "02_projections_locales.R"), encoding = "UTF-8")

cat("\nTerminé. Version de R :", R.version.string, "; fixest", as.character(packageVersion("fixest")), "\n")
