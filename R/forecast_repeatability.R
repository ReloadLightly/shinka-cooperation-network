#!/usr/bin/env Rscript
# Development-only fixed-fit repetition of the published reference forecast.
# No raw-archive access, new estimation or implicit regeneration of missing fits.
source("R/forecast.R")

assert_repeat_call <- function(x, effects) {
  stopifnot(all(c("include","fix","initialValue") %in% names(effects)),
            isTRUE(x$simOnly), x$nsub == 0L, x$n3 == 1000L,
            !isTRUE(x$cconditional), !isTRUE(x$useStdInits),
            all(effects$fix[effects$include]), any(effects$include))
  invisible(TRUE)
}

read_published_coefficients <- function(path) {
  # A column of empty CSV fields otherwise becomes logical NA during inference.
  # Empty interaction names are real native effect-key components, not missing.
  read.csv(path, stringsAsFactors=FALSE,
    colClasses=c(name="character",type="character",shortName="character",
                 interaction1="character",interaction2="character"))
}

run_fixed_repeat <- function(specfile, target, outdir, settingsfile, pastfile, coefficientfile) {
  if (!target %in% 2006:2009) stop("Only development targets 2006-2009 are admitted")
  fitfile <- file.path(outdir, "accepted_fit.rds")
  if (!file.exists(fitfile)) stop("Accepted fit missing: refitting is prohibited")
  settings <- read_json(settingsfile, simplifyVector=TRUE)
  seed <- settings$forecast$seed_override
  if (length(seed) != 1L || !seed %in% (target*1000L + 101:105))
    stop("Only the five declared fresh seeds are admitted")
  if (settings$forecast$simulations != 1000L) stop("Batch size must remain 1000")
  stopifnot(getRversion() == "4.2.1", packageVersion("RSiena") == "1.3.10")
  before <- unname(tools::md5sum(fitfile))
  expected <- read_published_coefficients(coefficientfile)
  stopifnot(all(expected$include), all(expected$fix), !anyDuplicated(effect_key(expected)))
  calls <- 0L
  scope <- new.env(parent=environment(run_forecast))
  # The old adapter's fallback can never start an estimation, even if a file
  # disappears between the outer existence check and the adapter's read.
  scope$fit_model <- function(...) stop("Refitting prohibited in repeatability study")
  scope$siena07 <- function(x, data, effects, ...) {
    assert_repeat_call(x, effects)
    used <- effects[effects$include,,drop=FALSE]
    index <- match(effect_key(used),effect_key(expected))
    stopifnot(nrow(used)==nrow(expected),!anyNA(index),
      isTRUE(all.equal(as.numeric(used$initialValue),as.numeric(expected$initialValue[index]),tolerance=1e-12)))
    calls <<- calls + 1L
    if (calls != 1L) stop("One native simulation call per batch is permitted")
    result <- RSiena::siena07(x, data=data, effects=effects, ...)
    stopifnot(all(result$fixed), isTRUE(all.equal(as.numeric(result$theta),
                   as.numeric(result$theta0), tolerance=0)))
    write_json(list(simOnly=TRUE, nsub=x$nsub, simulations=x$n3,
      seed=seed, all_coefficients_fixed=TRUE, coefficients_unchanged=TRUE,
      R=R.version.string, platform=R.version$platform, RSiena=as.character(packageVersion("RSiena")),
      published_forward_coefficients_verified=TRUE,
      effect_keys=as.list(effect_key(result$requestedEffects)),
      coefficients=as.list(as.numeric(result$theta))),
      file.path(outdir,"fixed_coefficient_audit.json"),
      pretty=TRUE, auto_unbox=TRUE, digits=16)
    result
  }
  fixed <- run_forecast
  environment(fixed) <- scope
  fixed(specfile, target, outdir, settingsfile, pastfile=pastfile)
  stopifnot(calls == 1L, identical(before, unname(tools::md5sum(fitfile))))
  invisible(TRUE)
}

if (sys.nframe() == 0L) {
  args <- commandArgs(trailingOnly=TRUE)
  if (identical(args, "--guard-self-test")) {
    # Contract test only. No fit, data packet, outcome or native simulation read.
    fixture <- data.frame(name=c("dv.net","milex.beh"),type="eval",
      shortName=c("density","behDenseTriads"),interaction1=c("","dv.net"),
      interaction2=c("",""),parm=c(0L,6L),include=TRUE,fix=TRUE,
      initialValue=c(-6,0.1),stringsAsFactors=FALSE)
    csv <- tempfile(fileext=".csv"); write.csv(fixture,csv,row.names=FALSE)
    # Reproduce the old failure, then check the typed reader preserves identity.
    legacy <- read.csv(csv,stringsAsFactors=FALSE)
    stopifnot(anyNA(legacy$interaction2),
      !identical(effect_key(legacy),effect_key(fixture)),
      identical(effect_key(read_published_coefficients(csv)),effect_key(fixture)))
    unlink(csv)
    x <- list(simOnly=TRUE,nsub=0,n3=1000,cconditional=FALSE,useStdInits=FALSE)
    effects <- data.frame(include=c(TRUE,TRUE),fix=c(TRUE,TRUE),initialValue=c(0.1,0.2))
    assert_repeat_call(x,effects)
    for (key in c("simOnly","nsub","n3","cconditional","useStdInits")) {
      bad <- x; bad[[key]] <- switch(key,simOnly=FALSE,nsub=3,n3=999,
                                    cconditional=TRUE,useStdInits=TRUE)
      stopifnot(inherits(try(assert_repeat_call(bad,effects),silent=TRUE),"try-error"))
    }
    effects$fix[1] <- FALSE
    stopifnot(inherits(try(assert_repeat_call(x,effects),silent=TRUE),"try-error"))
    cat("Fixed-fit guard contracts passed; zero native simulations.\n")
  } else {
    if (length(args) != 6L) stop("Usage: R/forecast_repeatability.R SPEC TARGET OUT SETTINGS PAST COEFFICIENTS")
    run_fixed_repeat(args[1],as.integer(args[2]),args[3],args[4],args[5],args[6])
  }
}
