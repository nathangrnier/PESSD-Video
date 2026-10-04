# =====================================================================================
# fonctions_lp.R : projections locales en panel (Jordà), erreurs-types de Driscoll-Kraay
#
# Modèle estimé à chaque horizon h :
#   y[i,t+h] - y[i,t-1] = a_i + m_mois + b_h * choc[t] + retards du choc (1..P)
#                         + retards de l'inflation (1..P) + contrôles (0..P) + erreur
#   y = 100 * log(indice de prix) ; choc = variation de 100 * log(prix mondial).
#   b_h se lit comme la réponse cumulée du niveau des prix, en %, h mois après une
#   hausse de 1 % du prix mondial.
# =====================================================================================

suppressPackageStartupMessages({
  library(data.table)
  library(fixest)
  library(ggplot2)
})

# ---------------------------------------------------------------------------------
# preparer_lp : met en forme le panel pour une variable dépendante donnée
#   dep         : nom de la colonne de prix (cpi_food_main, cpi_all_main, cpi_food, ...)
#   choc_var    : série mondiale dont la variation est le choc (fao_food par défaut)
#   fin         : dernier mois utilisé, y compris pour y[t+h]
#   neutraliser : data.table(iso3, date) de variations mensuelles à neutraliser ; toute
#                 observation dont la fenêtre (t-1, t+h] ou les retards contiennent un
#                 de ces mois est exclue
#   exclure_pays: pays retirés de l'estimation
# ---------------------------------------------------------------------------------
preparer_lp <- function(panel, dep, choc_var = "fao_food", fin = "2024-12", P = 12,
                        neutraliser = NULL, exclure_pays = NULL) {
  d <- copy(panel[date <= fin & !(iso3 %in% exclure_pays)])
  setkey(d, iso3, t)
  d[, y := 100 * log(get(dep))]
  d[exclu_gnb == TRUE, y := NA_real_]                 # Guinée-Bissau avant 2002-07
  d[, dy := y - shift(y), by = iso3]
  d[, neut := 0L]
  if (!is.null(neutraliser)) {
    d[neutraliser, on = .(iso3, date), neut := 1L]
    d[neut == 1L, dy := NA_real_]
  }
  d[, cum_neut := cumsum(neut), by = iso3]

  d[, choc := 100 * (log(get(choc_var)) - shift(log(get(choc_var)))), by = iso3]
  d[, choc_pos := pmax(choc, 0)]
  d[, choc_neg := pmin(choc, 0)]
  d[, d_oil := 100 * (log(oil_usd) - shift(log(oil_usd))), by = iso3]
  d[, d_fx  := 100 * (log(usd_xof) - shift(log(usd_xof))), by = iso3]

  # retards : choc et inflation de 1 à P, contrôles de 0 à P
  retards <- function(v, k) d[, paste0(v, "_l", k) := shift(get(v), k), by = iso3]
  for (v in c("choc", "choc_pos", "choc_neg", "dy")) retards(v, 1:P)
  for (v in c("d_oil", "d_fx", "gscpi")) retards(v, 0:P)
  attr(d, "P") <- P
  attr(d, "dep") <- dep
  d[]
}

# ---------------------------------------------------------------------------------
# estimer_lp : une régression par horizon
#   asym  : TRUE pour séparer hausses et baisses du prix mondial
#   inter : nom d'une caractéristique pays ; le choc et ses retards sont interagis avec
#           la caractéristique centrée sur la moyenne des pays
#   ef    : effets fixes (pays et mois calendaire par défaut)
#   dk    : fonction donnant le nombre de retards de Driscoll-Kraay selon h
# ---------------------------------------------------------------------------------
estimer_lp <- function(d, H = 0:24, controles = c("d_oil", "d_fx"), asym = FALSE, inter = NULL,
                       ef = "iso3 + mois", dk = function(h) h + 1, spec = "") {
  P <- attr(d, "P"); dep <- attr(d, "dep")
  d <- copy(d)
  lag_noms <- function(v, k) paste0(v, "_l", k)
  chocs <- if (asym) c("choc_pos", "choc_neg") else "choc"
  rhs <- c(chocs, unlist(lapply(chocs, lag_noms, k = 1:P)), lag_noms("dy", 1:P),
           unlist(lapply(controles, lag_noms, k = 0:P)))
  if (!is.null(inter)) {
    stopifnot(!asym)
    z <- unique(d[, .(iso3, z = get(inter))])
    stopifnot(nrow(z) == uniqueN(d$iso3), !anyNA(z$z))  # caractéristique fixe par pays
    z[, zc := z - mean(z)]
    d[z, on = "iso3", zc := i.zc]
    d[, choc_x := choc * zc]
    for (k in 1:P) d[, paste0("choc_x_l", k) := get(paste0("choc_l", k)) * zc]
    rhs <- c(rhs, "choc_x", paste0("choc_x_l", 1:P))
  }
  fml <- as.formula(paste("lhs ~", paste(rhs, collapse = " + "), "|", ef))

  res <- lapply(H, function(h) {
    d[, lhs := shift(y, -h) - shift(y, 1), by = iso3]
    # exclusion des fenêtres (t-1, t+h] contenant une variation neutralisée
    d[, n_fen := shift(cum_neut, -h) - shift(cum_neut, 1), by = iso3]
    d[!is.na(n_fen) & n_fen > 0, lhs := NA_real_]
    est <- feols(fml, data = d, vcov = vcov_DK(time = ~t, lag = dk(h)), notes = FALSE)
    b <- coef(est); V <- vcov(est)
    termes <- if (asym) c("choc_pos", "choc_neg") else if (!is.null(inter)) c("choc", "choc_x") else "choc"
    out <- data.table(h = h, terme = termes, coef = b[termes], se = sqrt(diag(V)[termes]))
    if (asym) {                                        # test d'égalité hausse = baisse
      diff <- b["choc_pos"] - b["choc_neg"]
      se_d <- sqrt(V["choc_pos", "choc_pos"] + V["choc_neg", "choc_neg"] - 2 * V["choc_pos", "choc_neg"])
      out <- rbind(out, data.table(h = h, terme = "hausse_moins_baisse", coef = diff, se = se_d))
    }
    out[, `:=`(nobs = nobs(est), pays = length(unique(d$iso3[obs(est)])))]
    out
  })
  res <- rbindlist(res)
  res[, `:=`(ic90_bas = coef - qnorm(0.95) * se, ic90_haut = coef + qnorm(0.95) * se,
             ic68_bas = coef - se, ic68_haut = coef + se,
             dep = dep, spec = spec)]
  setcolorder(res, c("spec", "dep", "terme", "h"))
  res[]
}

# ---------------------------------------------------------------------------------
# tracer_irf : réponses avec bandes à 68 % et 90 %
#   couleur : colonne distinguant les courbes d'un même panneau (facultatif)
#   facette : colonne définissant les panneaux (facultatif)
# ---------------------------------------------------------------------------------
tracer_irf <- function(res, fichier, titre, sous_titre = NULL, couleur = NULL, facette = NULL,
                       ruban = NULL, echelle_libre = FALSE,
                       ylab = "Réponse cumulée des prix (%, pour +1 % du prix mondial)",
                       largeur = 9, hauteur = 5) {
  # ruban : avec « couleur », modalités dont on trace la bande à 90 % (toutes par défaut)
  palette <- c("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
  res <- copy(res)
  p <- ggplot(res, aes(x = h, y = coef))
  if (is.null(couleur)) {
    p <- p + geom_ribbon(aes(ymin = ic90_bas, ymax = ic90_haut), fill = palette[1], alpha = 0.12) +
      geom_ribbon(aes(ymin = ic68_bas, ymax = ic68_haut), fill = palette[1], alpha = 0.18) +
      geom_line(colour = palette[1], linewidth = 0.9)
  } else {
    res[, (couleur) := factor(get(couleur), levels = unique(get(couleur)))]   # ordre d'apparition
    bandes <- if (is.null(ruban)) res else res[get(couleur) %in% ruban]
    p <- ggplot(res, aes(x = h, y = coef)) +
      geom_ribbon(data = bandes, aes(ymin = ic90_bas, ymax = ic90_haut, fill = .data[[couleur]]), alpha = 0.12, show.legend = FALSE) +
      geom_line(aes(colour = .data[[couleur]]), linewidth = 0.9) +
      scale_colour_manual(values = palette, name = NULL, drop = FALSE) +
      scale_fill_manual(values = palette, name = NULL, drop = FALSE)
  }
  p <- p + geom_hline(yintercept = 0, colour = "grey40", linewidth = 0.4) +
    scale_x_continuous(breaks = seq(0, 24, 6)) +
    labs(title = titre, subtitle = sous_titre, x = "Horizon (mois)", y = ylab) +
    theme_minimal(base_size = 11) +
    theme(legend.position = "bottom", panel.grid.minor = element_blank(),
          plot.title = element_text(face = "bold"))
  if (!is.null(facette)) p <- p + facet_wrap(as.formula(paste("~", facette)), labeller = label_wrap_gen(42),
                                             scales = if (echelle_libre) "free_y" else "fixed")
  ggsave(fichier, p, width = largeur, height = hauteur, dpi = 150, bg = "white")
  invisible(p)
}

# ---------------------------------------------------------------------------------
# reponse_du_choc : réponse du prix mondial à son propre choc, mêmes retards et mêmes
# contrôles. Une hausse de 1 % de l'indice FAO est en moyenne suivie d'autres hausses :
# rapporter la réponse des prix locaux à celle du prix mondial au même horizon donne
# un taux de transmission comparable d'un horizon à l'autre.
# ---------------------------------------------------------------------------------
reponse_du_choc <- function(d, choc_var = "fao_food", H = 0:24, controles = c("d_oil", "d_fx")) {
  P <- attr(d, "P")
  s <- unique(d[, c("t", "mois", choc_var, "choc", paste0("choc_l", 1:P),
                    unlist(lapply(controles, function(v) paste0(v, "_l", 0:P)))), with = FALSE])
  setkey(s, t)
  stopifnot(!anyDuplicated(s$t))                       # série commune à tous les pays
  s[, f := 100 * log(get(choc_var))]
  rhs <- c("choc", paste0("choc_l", 1:P), unlist(lapply(controles, function(v) paste0(v, "_l", 0:P))))
  fml <- as.formula(paste("lhs ~", paste(rhs, collapse = " + "), "| mois"))
  rbindlist(lapply(H, function(h) {
    s[, lhs := shift(f, -h) - shift(f, 1)]
    est <- feols(fml, data = s, notes = FALSE)
    data.table(h = h, reponse_prix_mondial = unname(coef(est)["choc"]))
  }))
}
