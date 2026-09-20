# Execute authors' original expressions, with per-siena07 checkpoints.
# "full" preserves every original scientific setting, seed and grid.
# "reduced" changes ONLY grid coverage and endpoint count, explicitly labelled.
args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 5L) stop("Usage: paper_abm.R ROOT RUN_DIR full|reduced MAX_NEW_CALLS all|equilibria")
project_root <- normalizePath(args[1])
run_dir <- normalizePath(args[2], mustWork=FALSE)
profile <- match.arg(args[3], c("full","reduced"))
max_new_calls <- as.integer(args[4])
stage <- match.arg(args[5],c("all","equilibria"))
stopifnot(is.finite(max_new_calls), max_new_calls >= 1)
library(reshape2)
library(sna)
library(igraph)
library(RSiena)
library(dplyr)
library(tidyr)
library(ggplot2)
library(jsonlite)
stopifnot(as.character(packageVersion("RSiena")) == "1.3.10")

for (d in c("work/data","work/scripts/ABM","work/output/abm",
             "work/figures_tables_main","work/figures_tables_appendix","checkpoints"))
    dir.create(file.path(run_dir,d), recursive=TRUE, showWarnings=FALSE)
src <- file.path(project_root,"sources/original/IO_Final")
Sys.chmod(list.files(file.path(run_dir,"work"), recursive=TRUE, full.names=TRUE), mode="0644")
file.copy(file.path(src,"data/data_raw.RData"),file.path(run_dir,"work/data"),overwrite=TRUE)
file.copy(file.path(src,"scripts/00.buildDataset"),file.path(run_dir,"work/scripts"),overwrite=TRUE)
for (f in c("00.getData","00.simulate","00.equilibria","00.makeFigures"))
    file.copy(file.path(src,"scripts/ABM",f),file.path(run_dir,"work/scripts/ABM"),overwrite=TRUE)

if (profile == "reduced") {
    p <- file.path(run_dir,"work/scripts/ABM/00.simulate")
    code <- readLines(p)
    code <- gsub("d.vals <- seq(-0.05, 0.05, 0.0025)","d.vals <- c(-0.05, 0, 0.05)",code,fixed=TRUE)
    code <- gsub("levs <- seq(-0.005, 0.005, 0.00025)","levs <- c(-0.005, 0, 0.005)",code,fixed=TRUE)
    code <- gsub("psi_lev <- seq(-0.005, 0, 0.00025)","psi_lev <- c(-0.005, -0.0025, 0)",code,fixed=TRUE)
    code <- gsub("eta_lev <- seq(-0.0001, 0, 0.000005)","eta_lev <- c(-0.0001, -0.00005, 0)",code,fixed=TRUE)
    code <- gsub("n3=25", "n3=4", code, fixed=TRUE)
    code <- gsub("n3=100", "n3=4", code, fixed=TRUE)
    writeLines(code,p)
    p <- file.path(run_dir,"work/scripts/ABM/00.equilibria")
    code <- readLines(p)
    code <- gsub("n3=10", "n3=4", code, fixed=TRUE)
    code <- gsub("c(1, seq(5, rc, 5))", "c(1, 100, 500)", code,fixed=TRUE)
    writeLines(code,p)
    p <- file.path(run_dir,"work/scripts/ABM/00.makeFigures")
    code <- readLines(p)
    code <- gsub("c(1, seq(5, rc, 5))", "c(1, 100, 500)", code,fixed=TRUE)
    writeLines(code,p)
}

.checkpoint <- new.env(parent=baseenv())
.checkpoint$counter <- 0L
.checkpoint$new_calls <- 0L
.checkpoint$run_dir <- run_dir
.checkpoint$profile <- profile
.checkpoint$stage <- stage
.checkpoint$limit <- max_new_calls
.checkpoint$source_hashes <- as.list(tools::md5sum(list.files(file.path(run_dir,"work/scripts"),recursive=TRUE,full.names=TRUE)))

siena07 <- function(...) {
    state <- .checkpoint
    state$counter <- state$counter + 1L
    call_args <- list(...)
    key_path <- file.path(state$run_dir,"checkpoints","key.tmp.rds")
    saveRDS(list(args=call_args, profile=state$profile, stage=state$stage, source=state$source_hashes),key_path,version=3)
    key <- unname(tools::md5sum(key_path))
    unlink(key_path)
    cache <- file.path(state$run_dir,"checkpoints",sprintf("call-%04d-%s.rds",state$counter,key))
    event <- list(call=state$counter, key=key, profile=state$profile,
                  timestamp=format(Sys.time(),tz="UTC",usetz=TRUE),
                  requested_n3=call_args[[1]]$n3)
    if (file.exists(cache)) {
        saved <- readRDS(cache)
        assign(".Random.seed",saved$rng,envir=.GlobalEnv)
        event$status <- "resumed_from_checkpoint"
        cat(toJSON(event,auto_unbox=TRUE),"\n",file=file.path(state$run_dir,"calls.jsonl"),append=TRUE)
        return(saved$result)
    }
    if (state$new_calls >= state$limit) {
        event$status <- "paused_at_declared_call_budget"
        cat(toJSON(event,auto_unbox=TRUE),"\n",file=file.path(state$run_dir,"calls.jsonl"),append=TRUE)
        write_json(list(status="resumable",next_call=state$counter,profile=state$profile),
                   file.path(state$run_dir,"manifest.json"),auto_unbox=TRUE,pretty=TRUE)
        quit(save="no", status=75L)
    }
    event$status <- "started"
    cat(toJSON(event,auto_unbox=TRUE),"\n",file=file.path(state$run_dir,"calls.jsonl"),append=TRUE)
    start <- proc.time()
    result <- do.call(RSiena::siena07,call_args)
    state$new_calls <- state$new_calls + 1L
    saveRDS(list(result=result,rng=get(".Random.seed",envir=.GlobalEnv)),paste0(cache,".tmp"))
    file.rename(paste0(cache,".tmp"),cache)
    event$status <- "completed"
    event$elapsed_seconds <- unname((proc.time()-start)["elapsed"])
    event$returned_simulations <- length(result$sims)
    event$result_bytes <- as.numeric(object.size(result))
    event$memory <- grep("VmPeak|VmHWM|VmRSS",readLines("/proc/self/status"),value=TRUE)
    cat(toJSON(event,auto_unbox=TRUE),"\n",file=file.path(state$run_dir,"calls.jsonl"),append=TRUE)
    result
}

setwd(file.path(run_dir,"work"))
seed <- 12345
set.seed(seed)
source("scripts/ABM/00.getData")
gc()
write_json(list(profile=profile, stage=stage, actors=N, seed=seed,
                calibration_years=c(2000,2001),
    full_requested_calls=665L,full_requested_endpoints=21260L,
                stage_requested_calls=if(stage=="equilibria")if(profile=="full")101L else 3L else if(profile=="full")665L else 21L,
                country_sample_reduced=FALSE),
           file.path(run_dir,"calibration.json"),pretty=TRUE,auto_unbox=TRUE)
if(stage == "all") {
    source("scripts/ABM/00.simulate")
} else {
    # Original simulation prelude builds the exact data/effect objects; stop
    # before any grid simulation. Equilibria resets all scientific parameters.
    expressions <- readLines("scripts/ABM/00.simulate")
    boundary <- which(expressions == "## Simulate at different values of degree parameter")[1]
    stopifnot(is.finite(boundary))
    eval(parse(text=expressions[seq_len(boundary-1L)]))
}
source("scripts/ABM/00.equilibria")
if(stage == "all") {
    library(viridis)
    library(patchwork)
    source("scripts/ABM/00.makeFigures")
}
write_json(list(status="completed",profile=profile,calls=.checkpoint$counter,
                stage=stage,
                scientific_claim=if(profile=="full") "Original ABM grid executed; inspect output and discrepancies" else "Reduced diagnostic only; not Figures 5-7 reproduced"),
           file.path(run_dir,"manifest.json"),auto_unbox=TRUE,pretty=TRUE)
