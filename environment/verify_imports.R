options(warn=1)
packages <- c("countrycode", "gdata", "reshape2", "texreg", "maps", "RColorBrewer", "viridis", "grid", "patchwork", "igraph", "HiveR", "RSiena", "plyr", "dplyr", "tidyverse", "xtable", "PRROC", "Metrics", "hydroGOF", "rms", "geepack", "sna")
for (package in packages) {
  suppressPackageStartupMessages(library(package, character.only=TRUE))
  cat(package, as.character(packageVersion(package)), "loaded\n")
}
cat("Every package imported by 01.mainPaper.R, 02.appendix.R and 03.ABM.R loaded.\n")
