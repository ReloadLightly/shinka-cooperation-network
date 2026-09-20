stopifnot(getRversion() == "4.2.1")
stopifnot(packageVersion("RSiena") == "1.3.10")
stopifnot(packageVersion("PRROC") == "1.3.1")
packages <- c("RSiena", "PRROC", "data.table", "network", "igraph", "sna", "reshape2", "xtable", "ggplot2", "jsonlite", "dplyr", "tidyr", "viridis", "patchwork", "tidyverse", "countrycode", "gdata", "texreg", "maps", "Metrics", "hydroGOF", "rms", "geepack", "HiveR")
versions <- lapply(packages, function(p) list(package=p, version=as.character(packageVersion(p))))
installed <- installed.packages()
write.table(installed[,c("Package", "Version", "Built")], "environment/r-packages.tsv", sep="\t", row.names=FALSE, quote=FALSE)
dir.create("environment", showWarnings=FALSE)
jsonlite::write_json(list(timestamp_utc=format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz="UTC"), R=R.version.string, platform=R.version$platform, packages=versions), "environment/versions.json", auto_unbox=TRUE, pretty=TRUE)
capture.output(sessionInfo(), file="environment/session-info.txt")
print(sessionInfo())
# PRROC class0 = positive class; exact agreement on a perfectly ranked toy set.
perfect <- PRROC::pr.curve(scores.class0=c(0.9,0.8), scores.class1=c(0.2,0.1), curve=FALSE)$auc.integral
stopifnot(is.finite(perfect), abs(perfect-1) < 1e-12)
interleaved <- PRROC::pr.curve(scores.class0=c(0.8,0.4), scores.class1=c(0.6,0.2), curve=FALSE)$auc.integral
stopifnot(abs(interleaved-0.79726744594591781) < 1e-14)
jsonlite::write_json(list(package="PRROC", version=as.character(packageVersion("PRROC")), positive_class_argument="scores.class0", negative_class_argument="scores.class1", curve=FALSE, field="auc.integral", perfect_ranking_auc=perfect, interleaved=list(positive=c(0.8,0.4), negative=c(0.6,0.2), auc=interleaved)), "environment/prroc-verification.json", pretty=TRUE, auto_unbox=TRUE, digits=17)
cat("Exact R/RSiena/PRROC versions and PRROC positive-class semantics verified.\n")
