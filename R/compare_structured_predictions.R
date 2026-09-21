#!/usr/bin/env Rscript
# Compare prediction payloads, not RDS bytes (structured metadata may differ).
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==2L)
a <- readRDS(args[1]); b <- readRDS(args[2])
fields <- c("nms","probabilities","behavior_mean","origin_network","origin_behavior",
            "origin_active","target","simulations","seed","forecast_schema_version","native_origin_active")
for(field in fields) {
  if(!field%in%names(a)||!field%in%names(b)||!identical(a[[field]],b[[field]]))
    stop("Forced structured/reference forecast mismatch in ",field)
}
cat("PASS: every compared prediction field is identical; no target file opened.\n")
