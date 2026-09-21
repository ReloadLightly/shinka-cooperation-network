# Step 3A only: deterministic saved-fit checks and a stopped native initialization.
# No path in this script is permitted to generate a new simulation.
source("R/empirical.R")

identity_columns <- c("name", "type", "shortName", "interaction1", "interaction2",
  "parm", "period", "group", "groupName", "rateType", "basicRate", "effect1",
  "effect2", "effect3", "timeDummy", "setting")

assert <- function(ok, message) if (!isTRUE(ok)) stop(message, call.=FALSE)
same_numbers <- function(a, b, tolerance=1e-12) {
  identical(dim(a),dim(b)) && length(a)==length(b) && all(is.finite(a)) &&
    all(is.finite(b)) && max(abs(as.numeric(a)-as.numeric(b)),0)<=tolerance
}

# Period/group are essential: the legacy forecast effect_key omits rate periods.
# Use a lossless JSON array per row, preserving empty strings and genuine NA.
parameter_keys <- function(e) {
  assert(all(identity_columns %in% names(e)), "Missing native parameter identity field")
  vapply(seq_len(nrow(e)), function(i) {
    row <- lapply(identity_columns,function(n) {
      x <- e[[n]][i]
      if(is.na(x)) NULL else as.character(x)
    })
    as.character(toJSON(row,auto_unbox=TRUE,null="null",na="null"))
  }, character(1))
}

bind_saved_theta <- function(e, fit) {
  selected <- which(e$include)
  saved <- fit$requestedEffects
  assert(nrow(saved)==length(fit$theta), "Saved parameter dimension mismatch")
  old <- parameter_keys(saved); new <- parameter_keys(e[selected,,drop=FALSE])
  assert(!anyDuplicated(old) && !anyDuplicated(new), "Duplicate native parameter identity")
  assert(length(old)==length(new) && setequal(old,new), "Rebuilt model has different effects")
  index <- match(new,old)
  assert(identical(as.logical(e$fix[selected]),as.logical(saved$fix[index])), "Fixed flags differ")
  assert(identical(as.logical(e$test[selected]),as.logical(saved$test[index])), "Test flags differ")
  e$initialValue[selected] <- fit$theta[index]
  list(effects=e, saved_index=index, keys=new, selected=selected)
}

# The scoped reference has non-degenerate moments; never silently regularize a
# singular matrix or substitute a standard error / Dolby-adjusted statistic.
reconstruct_diagnostics <- function(sf, fixed) {
  assert(is.matrix(sf) && nrow(sf)>1L && ncol(sf)>0L && all(is.finite(sf)), "Invalid moment matrix")
  assert(is.logical(fixed) && length(fixed)==ncol(sf) && !anyNA(fixed), "Invalid fixed flags")
  m <- colMeans(sf); V <- cov(sf)
  assert(all(diag(V)>0), "Zero-variance moment requires native special-case review")
  t <- m/sqrt(diag(V)); free <- which(!fixed)
  assert(length(free)>0L, "All fixed parameters would remove the convergence diagnostic")
  overall <- sqrt(drop(crossprod(m[free],solve(V[free,free,drop=FALSE],m[free]))))
  assert(is.finite(overall), "Nonfinite overall convergence")
  list(mean=m,covariance=V,t_ratios=t,overall=overall,maximum_absolute_t=max(abs(t)),free_count=length(free))
}

# Copy original algorithm settings, not a default initializer. Resolve the FRAN
# callback by its pinned namespace name instead of reusing a serialized closure.
prepare_algorithm <- function(fit, prefix, n3=3000L, seed=2009301L) {
  x <- fit$x
  assert(inherits(x,"sienaAlgorithm"), "Saved algorithm class mismatch")
  assert(identical(x$FRANname,"simstats0c"), "Unexpected native simulator")
  for(n in c("maxlike","gmm","simOnly","cconditional","useStdInits","FinDiff.method"))
    assert(identical(x[[n]],FALSE), paste("Unexpected original algorithm flag",n))
  assert(identical(unname(x$modelType),3) && identical(names(x$modelType),"dv.net"), "Network model differs")
  assert(identical(unname(x$behModelType),1) && identical(names(x$behModelType),"milex.beh"), "Behavior model differs")
  assert(n3==3000L && seed==2009301L, "Undeclared pilot design")
  x$nsub <- 0L; x$n3 <- as.integer(n3); x$randomSeed <- as.integer(seed)
  x$projname <- prefix
  x$FRAN <- "simstats0c" # robmon resolves this after guards are installed.
  for(n in setdiff(names(fit$x),c("nsub","n3","randomSeed","projname","FRAN")))
    assert(identical(x[[n]],fit$x[[n]]),paste("Original setting changed",n))
  x
}

# This exercises actual siena07/robmon/initializeFRAN control flow. Traces abort
# before the phase3 body. Entry to optimization or a simulator is a hard error.
# The namespace is restored on exit. This is not a completed diagnostic run.
stopped_native_initialization <- function(fit, netdata, effects, algorithm) {
  ns <- asNamespace("RSiena")
  state <- new.env(parent=emptyenv());state$phase3_entries <- 0L
  state$forbidden_entries <- 0L;state$capture <- NULL
  block <- function() {
    state$forbidden_entries <- state$forbidden_entries+1L
    stop("Forbidden optimization/simulation entry during step 3A",call.=FALSE)
  }
  capture <- function(z,x) {
    state$phase3_entries <- state$phase3_entries+1L
    assert(x$nsub==0L && identical(x$simOnly,FALSE) && x$n3==3000L, "Wrong diagnostic route")
    assert(z$n==0 && !isTRUE(z$cconditional), "Optimization/conditioning detected")
    assert(identical(as.numeric(z$theta),as.numeric(fit$theta)), "Native initialization moved coefficients")
    assert(identical(parameter_keys(z$requestedEffects),parameter_keys(fit$requestedEffects)), "Native parameter ordering differs")
    assert(identical(as.logical(z$fixed),as.logical(fit$fixed)), "Native fixed flags differ")
    assert(!any(z$fixed), "Reference must retain all 58 diagnostic coordinates")
    assert(same_numbers(z$targets,fit$targets), "Reconstructed observed targets differ")
    assert(same_numbers(z$targets2,fit$targets2), "Reconstructed per-period targets differ")
    assert(z$observations==19L && z$pp==58L, "Native training scope differs")
    state$capture <- list(coefficients_identical=TRUE,parameter_order_identical=TRUE,
      fixed_flags_identical=TRUE,free_coordinates=sum(!z$fixed),
      observed_targets_equal=TRUE,period_targets_equal=TRUE,
      maximum_target_difference=max(abs(z$targets-fit$targets)),
      maximum_period_target_difference=max(abs(z$targets2-fit$targets2)),
      observations=z$observations,periods=z$observations-1L,optimization_iterations=z$n,
      nsub=x$nsub,n3=x$n3,simOnly=x$simOnly,seed=x$randomSeed,
      phase3_body_entered=FALSE,simulator_entered=FALSE)
    stop(structure(list(message="Expected stop before phase3 body",call=NULL),
      class=c("step3a_expected_stop","error","condition")))
  }
  guarded <- c("phase1.1","phase1.2","phase2.1","proc2subphase","simstats0c","maxlikec")
  traced <- character()
  on.exit(for(n in rev(traced)) untrace(n,where=ns),add=TRUE)
  for(n in guarded) {
    assert(exists(n,envir=ns,inherits=FALSE),paste("Missing guard target",n))
    trace(n,tracer=block,print=FALSE,where=ns);traced <- c(traced,n)
  }
  tracer <- substitute(CAPTURE(z,x),list(CAPTURE=capture))
  trace("phase3",tracer=tracer,print=FALSE,where=ns);traced <- c(traced,"phase3")
  stopped <- tryCatch({
    siena07(algorithm,data=netdata,effects=effects,prevAns=NULL,batch=TRUE,
      silent=TRUE,useCluster=FALSE,returnDeps=FALSE)
    FALSE
  },step3a_expected_stop=function(e) TRUE)
  assert(stopped && state$phase3_entries==1L && state$forbidden_entries==0L,
    "No verified, simulation-free stop at phase3 entry")
  state$capture
}

native_source_check <- function(source_root) {
  # Verify the actual loaded functions, not only a version string on disk.
  mapping <- list("R/siena07.r"=c("siena07"),"R/robmon.r"=c("robmon"),
    "R/initializeFRAN.r"=c("initializeFRAN"),
    "R/simstatsc.r"=c("simstats0c"),"R/terminateFRAN.r"=c("terminateFRAN"),
    "R/phase3.r"=c("phase3","phase3.2","CalculateDerivative3","PotentialNR"))
  ns <- asNamespace("RSiena");out <- list()
  for(path in names(mapping)) {
    expressions <- parse(file.path(source_root,path))
    for(n in mapping[[path]]) {
      matches <- Filter(function(e)is.call(e) && identical(e[[1]],as.name("<-")) &&
        identical(e[[2]],as.name(n)) && is.call(e[[3]]) && identical(e[[3]][[1]],as.name("function")),as.list(expressions))
      assert(length(matches)==1L,paste("Ambiguous source function",n))
      expected <- eval(matches[[1]][[3]],envir=ns);actual <- get(n,envir=ns)
      assert(identical(body(actual),body(expected)) && identical(formals(actual),formals(expected)),
        paste("Loaded function differs from pinned source",n))
      out[[n]] <- list(source=path,loaded_body_and_formals_match=TRUE)
    }
  }
  out
}

self_test <- function() {
  tests <- 0L
  expect_error <- function(code) {
    assert(inherits(try(force(code),silent=TRUE),"try-error"),"Expected guard refusal")
    tests <<- tests+1L
  }
  # Deterministic numbers, no RNG use and no network simulation.
  sf <- cbind(c(-2,-1,0,1,2,3),c(1,-2,3,-1,0,2))
  r <- reconstruct_diagnostics(sf,c(FALSE,FALSE))
  assert(same_numbers(r$t_ratios,colMeans(sf)/apply(sf,2,sd)),"SD denominator mismatch");tests<-tests+1L
  free <- reconstruct_diagnostics(sf,c(FALSE,TRUE))
  assert(abs(free$overall-abs(r$t_ratios[1]))<1e-12,"Fixed-coordinate exclusion mismatch");tests<-tests+1L
  expect_error(reconstruct_diagnostics(sf,c(TRUE,TRUE)))
  expect_error(reconstruct_diagnostics(sf,c(FALSE)))
  expect_error(reconstruct_diagnostics(cbind(sf[,1],sf[,1]),c(FALSE,FALSE)))
  expect_error(reconstruct_diagnostics(cbind(sf[,1],0),c(FALSE,FALSE)))
  bad<-sf;bad[1,1]<-NA_real_;expect_error(reconstruct_diagnostics(bad,c(FALSE,FALSE)))
  e<-as.data.frame(setNames(rep(list(rep("",2L)),length(identity_columns)),identity_columns),stringsAsFactors=FALSE)
  e$period<-1:2;e$parm<-0;e$fix<-FALSE;e$test<-FALSE;e$include<-TRUE;e$initialValue<-0
  f<-list(requestedEffects=e,theta=c(1.25,2.75))
  b<-bind_saved_theta(e[2:1,],f)
  assert(identical(b$effects$initialValue,c(2.75,1.25)),"Period-specific binding failed");tests<-tests+1L
  duplicate<-e;duplicate$period<-1L;expect_error(bind_saved_theta(duplicate,f))
  mismatch<-e;mismatch$fix[1]<-TRUE;expect_error(bind_saved_theta(mismatch,f))
  changed<-e;changed$parm[1]<-99;expect_error(bind_saved_theta(changed,f))
  list(status="passed",checks=tests,simulations=0L,refits=0L)
}

run_preflight <- function(root, output) {
  policy <- read_json(file.path(root,"configs/convergence-preflight-v1.json"),simplifyVector=TRUE)
  assert(as.character(getRversion())=="4.2.1" && as.character(packageVersion("RSiena"))=="1.3.10", "Wrong pinned runtime")
  sources <- native_source_check(file.path(root,"vendor/RSiena"))
  checks <- self_test()
  packet <- readRDS(file.path(output,"training-packet.rds"))
  assert(identical(as.integer(packet$years),1990:2008),"Training years differ")
  assert(length(packet$nms)==161L && identical(as.numeric(packet$nms),sort(as.numeric(packet$nms))),"Actor universe/order differs")
  fit <- readRDS(file.path(root,policy$fit_path))
  assert(isTRUE(fit$OK) && identical(fit$termination,"OK"),"Incomplete original fit")
  assert(length(fit$theta)==58L && nrow(fit$sf)==1000L && ncol(fit$sf)==58L && fit$Phase3nits==1000L,"Saved matrix dimensions differ")
  assert(!any(fit$fixed) && !any(fit$diver) && !any(fit$newFixed),"Original native flags differ")
  assert(identical(as.logical(fit$fixed),as.logical(fit$requestedEffects$fix)),"Saved fixed flags inconsistent")
  d <- reconstruct_diagnostics(fit$sf,fit$fixed)
  assert(same_numbers(d$t_ratios,fit$tconv) && abs(d$overall-fit$tconv.max)<1e-12,"Saved convergence reconstruction differs")
  assert(same_numbers(d$covariance,fit$msf),"Saved covariance reconstruction differs")
  original <- fit_diagnostics(fit,1000L)
  assert(identical(original$valid,FALSE) && isTRUE(original$finite_identified),"Historical status unexpectedly differs")
  assert(abs(d$overall-policy$original_diagnostics$overall)<1e-12 &&
    abs(d$maximum_absolute_t-policy$original_diagnostics$max_abs_t)<1e-12,"Historical convergence record differs")
  netdata <- make_training_data(packet)
  bound <- bind_saved_theta(model_effects(netdata),fit)
  algorithm <- prepare_algorithm(fit,file.path(output,"stopped-initialization"))
  before <- fit$theta
  dry <- stopped_native_initialization(fit,netdata,bound$effects,algorithm)
  assert(identical(before,fit$theta),"Saved theta changed in memory")
  table <- fit$requestedEffects[,identity_columns,drop=FALSE]
  table$fit_index <- seq_along(fit$theta);table$theta <- fit$theta
  table$observed_target <- fit$targets;table$saved_t_ratio <- d$t_ratios
  write.csv(table,file.path(output,"parameter-map.csv"),row.names=FALSE,na="NA")
  write.csv(d$covariance,file.path(output,"saved-moment-covariance.csv"),row.names=FALSE)
  write.csv(data.frame(index=seq_along(d$mean),mean=d$mean),file.path(output,"saved-moment-means.csv"),row.names=FALSE)
  report <- list(status="verified_no_simulation",stage="3A",training_years=packet$years,
    actors=length(packet$nms),observations=length(packet$years),periods=length(packet$years)-1L,
    parameter_count=length(fit$theta),network_rates=sum(fit$requestedEffects$name=="dv.net" & fit$requestedEffects$basicRate),
    behavior_rates=sum(fit$requestedEffects$name=="milex.beh" & fit$requestedEffects$basicRate),
    network_objective=sum(fit$requestedEffects$name=="dv.net" & !fit$requestedEffects$basicRate),
    behavior_objective=sum(fit$requestedEffects$name=="milex.beh" & !fit$requestedEffects$basicRate),
    original_diagnostics=list(draws=nrow(fit$sf),maximum_absolute_t=d$maximum_absolute_t,
      overall=d$overall,individual_pass=d$maximum_absolute_t<0.1,overall_pass=d$overall<0.25,
      full_original_acceptance=original$valid,covariance_reconstruction_max_error=max(abs(d$covariance-fit$msf)),
      t_ratio_reconstruction_max_error=max(abs(d$t_ratios-fit$tconv)),
      overall_reconstruction_error=abs(d$overall-fit$tconv.max)),
    dry_initialization=dry,source_function_verification=sources,self_tests=checks,
    saved_fit_contains_reusable_training_data=FALSE,
    interpretation="Recomputed OLD 1000-draw diagnostics and verified initialization only. The 3000-draw pilot has NOT run. No new convergence observation, uncertainty estimate or acceptance decision.",
    new_simulations=0L,new_fits=0L,new_forecasts=0L,target_packets_read=0L,raw_archives_read=0L,
    pilot=list(status="prepared_not_executed",seed=2009301L,n3=3000L,nsub=0L,simOnly=FALSE,
      coefficient_source="fit$theta mapped by complete effect identities including period and group",
      previous_answer=NULL,keep_original_fixed_flags=TRUE,thresholds=c(individual=0.1,overall=0.25),
      remaining_checks=c("Actual 3000-draw completion","Coefficient invariance throughout and after simulation",
        "Fresh diagnostics and numerical warnings","Measured runtime and peak memory")))
  write_json(report,file.path(output,"verification.json"),auto_unbox=TRUE,pretty=TRUE,na="null",digits=17)
  writeLines(capture.output(sessionInfo()),file.path(output,"session-info.txt"))
  report
}

args <- commandArgs(trailingOnly=TRUE)
if(identical(args,"--self-test")) {
  cat(toJSON(self_test(),auto_unbox=TRUE,pretty=TRUE),"\n")
} else {
  assert(length(args)==3L && args[1]=="--verify-only", "Use --self-test or --verify-only ROOT OUTPUT; numerical execution is unavailable")
  result <- run_preflight(normalizePath(args[2]),normalizePath(args[3]))
  cat(toJSON(result,auto_unbox=TRUE,pretty=TRUE,digits=17),"\n")
}
