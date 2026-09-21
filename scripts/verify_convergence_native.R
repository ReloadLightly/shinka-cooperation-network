# Read-only post-run evidence verification. No native simulations are permitted.
suppressPackageStartupMessages(library(RSiena))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(getRversion())=="4.2.1", as.character(packageVersion("RSiena"))=="1.3.10")
expr <- parse('R/convergence_preflight.R')
cli <- which(vapply(as.list(expr),function(e)is.call(e)&&identical(e[[1]],as.name('<-'))&&identical(e[[2]],as.name('args')),logical(1)))
stopifnot(length(cli)==1L)
for(e in as.list(expr)[seq_len(cli-1L)])eval(e,.GlobalEnv)
ns <- asNamespace('RSiena'); block <- function()stop('No simulation or estimation allowed during evidence review')
for(n in c('siena07','simstats0c','phase3','phase1.1','phase1.2','phase2.1','maxlikec'))trace(n,tracer=block,print=FALSE,where=ns)
p <- read_json('configs/convergence-repeatability-v1.json',simplifyVector=TRUE)
out <- 'results/diagnostics/convergence-repeatability-v1'
records <- list()
for(label in names(p$fits)) {
  original <- readRDS(p$fits[[label]]$path)
  if(label=='attempt4')original <- original$fit
  stopifnot(inherits(original,'sienaFit'))
  for(seed in p$fits[[label]]$seeds) {
    pilot <- label=='attempt3' && seed==2009301L
    folder <- if(pilot)'results/diagnostics/convergence-pilot-v1' else file.path(out,label,seed)
    raw <- readRDS(file.path(folder,'raw-phase3.rds'))
    native <- readRDS(file.path(folder,if(pilot)'diagnostic.rds' else 'native-diagnostic.rds'))
    report <- read_json(file.path(folder,'summary.json'),simplifyVector=TRUE)
    stopifnot(identical(as.numeric(raw$theta),as.numeric(original$theta)),
      identical(as.numeric(native$theta),as.numeric(original$theta)),
      identical(raw$fixed,original$fixed),identical(native$fixed,original$fixed),
      identical(parameter_keys(raw$requestedEffects),parameter_keys(original$requestedEffects)),
      identical(parameter_keys(native$requestedEffects),parameter_keys(original$requestedEffects)),
      same_numbers(raw$targets,original$targets,0),same_numbers(raw$targets2,original$targets2,0),
      identical(dim(raw$sf),c(3000L,58L)),all(is.finite(raw$sf)),
      identical(dim(raw$ssc),dim(raw$sf2)), all(is.finite(raw$ssc)), all(is.finite(raw$sf2)),
      identical(as.integer(dim(raw$ssc)),c(3000L,18L,58L)))
    sf_csv <- as.matrix(read.csv(file.path(folder,'moment-deviations.csv')))
    stopifnot(isTRUE(all.equal(unname(raw$sf),unname(sf_csv),tolerance=1e-12,check.attributes=FALSE)))
    full <- reconstruct_diagnostics(raw$sf,raw$fixed)
    prefix <- reconstruct_diagnostics(raw$sf[1:1000,,drop=FALSE],raw$fixed)
    stopifnot(same_numbers(full$covariance,native$msf),
      same_numbers(full$t_ratios,native$tconv),
      abs(full$overall-as.numeric(native$tconv.max))<1e-12,
      abs(full$overall-report$fresh_full_3000$overall)<1e-12,
      abs(prefix$overall-report$fresh_first_1000$overall)<1e-12)
    native$sf <- raw$sf
    checked <- fit_diagnostics(native,3000L)
    stopifnot(identical(checked$valid,report$native_diagnostics$valid))
    records[[length(records)+1L]] <- list(fit=label,seed=seed,pilot_reused=pilot,
      coefficients_match_original_exactly=TRUE,parameter_order_and_flags_match=TRUE,
      raw_score_and_moment_arrays_complete=TRUE,targets_match_original_exactly=TRUE,
      csv_matches_raw_rds=TRUE,native_diagnostics_recomputed=TRUE,native_valid=checked$valid,
      prefix_overall=prefix$overall,full_overall=full$overall)
  }
}
write_json(list(status='verified',scope='read_only',new_simulations=0L,new_refits=0L,
  target_packets_read=0L,raw_archives_read=0L,cells=records),file.path(out,'native-evidence-verification.json'),
  auto_unbox=TRUE,pretty=TRUE,digits=17)
cat('Verified all 10 native evidence bundles against their saved original coefficients. No simulations.\n')
