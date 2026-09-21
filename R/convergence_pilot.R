# Step 3B: one phase-3-only diagnostic, never parameter optimization.
source("R/empirical.R")
# Import only named helper declarations, not Step 3A's command-line driver.
helper_names <- c("identity_columns","assert","same_numbers","parameter_keys",
  "bind_saved_theta","reconstruct_diagnostics","prepare_algorithm","native_source_check")
loaded <- character()
for(e in parse("R/convergence_preflight.R")) {
  if(is.call(e) && identical(e[[1]],as.name("<-")) &&
     as.character(e[[2]]) %in% helper_names) {
    eval(e,envir=.GlobalEnv); loaded <- c(loaded,as.character(e[[2]]))
  }
}
stopifnot(setequal(loaded,helper_names))

check_simulation_state <- function(z, theta, finite_difference=FALSE) {
  assert(identical(as.numeric(z$theta),as.numeric(theta)),"Simulator coefficient vector changed")
  assert(identical(as.numeric(z$Phase),3),"Simulator entered outside phase 3")
  assert(identical(finite_difference,FALSE) && identical(z$FinDiff.method,FALSE),"Finite-difference perturbation forbidden")
  assert(!isTRUE(z$maxlike) && !isTRUE(z$gmm) && !isTRUE(z$cconditional) && is.null(z$cl),"Wrong native simulation route")
}

pilot_self_test <- function() {
  z <- list(theta=c(1,2),Phase=3,FinDiff.method=FALSE,maxlike=FALSE,gmm=FALSE,cconditional=FALSE,cl=NULL)
  check_simulation_state(z,c(1,2)); n <- 1L
  for(change in list(list(theta=c(1,3)),list(Phase=2),list(FinDiff.method=TRUE),
    list(maxlike=TRUE),list(gmm=TRUE),list(cconditional=TRUE),list(cl=list(1)))) {
    bad <- z;bad[names(change)] <- change
    assert(inherits(try(check_simulation_state(bad,c(1,2)),silent=TRUE),"try-error"),"Guard should reject changed state")
    n <- n+1L
  }
  assert(inherits(try(check_simulation_state(z,c(1,2),TRUE),silent=TRUE),"try-error"),"Finite difference flag not blocked")
  list(status="passed",checks=n+1L,new_simulations=0L)
}

run_pilot <- function(root,out) {
  assert(as.character(getRversion())=="4.2.1" && as.character(packageVersion("RSiena"))=="1.3.10","Wrong pinned runtime")
  sources <- native_source_check(file.path(root,"vendor/RSiena"))
  policy <- read_json(file.path(root,"configs/convergence-preflight-v1.json"),simplifyVector=TRUE)
  packet <- readRDS(file.path(out,"training-packet.rds"))
  assert(identical(as.integer(packet$years),1990:2008) && length(packet$nms)==161L,"Wrong training scope")
  original <- readRDS(file.path(root,policy$fit_path)); theta <- original$theta
  assert(length(theta)==58L && !any(original$fixed) && !any(original$diver),"Wrong saved fit")
  old <- reconstruct_diagnostics(original$sf,original$fixed)
  assert(abs(old$overall-policy$original_diagnostics$overall)<1e-12,"Historical diagnostic differs")
  assert(identical(fit_diagnostics(original,1000L)$valid,FALSE),"Historical acceptance must remain failed")
  netdata <- make_training_data(packet)
  bound <- bind_saved_theta(model_effects(netdata),original)
  algorithm <- prepare_algorithm(original,file.path(out,"native-phase3"))
  ns <- asNamespace("RSiena"); state <- new.env(parent=emptyenv())
  state$simulator_calls <- 0L;state$phase3_entries <- 0L;state$forbidden_entries <- 0L
  state$newton_checks <- 0L;state$warnings <- character();state$initialization_verified <- FALSE
  record <- function(status,error=NULL) {
    write_json(list(status=status,stage="3B",seed=2009301L,n3=3000L,
      simulator_calls=state$simulator_calls,phase3_entries=state$phase3_entries,
      forbidden_entries=state$forbidden_entries,newton_checks=state$newton_checks,
      initialization_verified=state$initialization_verified,warnings=state$warnings,error=error),
      file.path(out,"native-state.json"),auto_unbox=TRUE,pretty=TRUE,null="null",digits=17)
  }
  block <- function() {
    state$forbidden_entries <- state$forbidden_entries+1L
    stop("Optimization/alternate simulator forbidden in Step 3B",call.=FALSE)
  }
  enter <- function(z,x) {
    state$phase3_entries <- state$phase3_entries+1L
    assert(state$phase3_entries==1L && z$n==0,"Automatic restart or optimization detected")
    assert(x$nsub==0L && x$n3==3000L && identical(x$simOnly,FALSE) && x$randomSeed==2009301L,"Pilot settings changed")
    assert(identical(as.numeric(z$theta),as.numeric(theta)),"Initialization moved theta")
    assert(identical(parameter_keys(z$requestedEffects),parameter_keys(original$requestedEffects)),"Native effect order differs")
    assert(identical(as.logical(z$fixed),as.logical(original$fixed)) && !any(z$fixed),"Fixed flags changed")
    assert(same_numbers(z$targets,original$targets,0) && same_numbers(z$targets2,original$targets2,0),"Observed targets changed")
    assert(z$observations==19L && z$pp==58L && !isTRUE(z$cconditional),"Training/model scope differs")
    state$initialization_verified <- TRUE;record("phase3_entered")
  }
  simulation <- function(z,fromFiniteDiff) {
    assert(state$initialization_verified && state$phase3_entries==1L,"Simulation before verified initialization")
    check_simulation_state(z,theta,fromFiniteDiff)
    state$simulator_calls <- state$simulator_calls+1L
    assert(state$simulator_calls<=3000L,"Declared draw budget exceeded")
    if(state$simulator_calls %% 250L==0L) {
      record("running");cat("Verified unchanged theta at native call",state$simulator_calls,"of 3000\n");flush.console()
    }
  }
  newton <- function(z,x,MakeStep) {
    assert(identical(MakeStep,FALSE),"Applying a Newton update is forbidden")
    assert(identical(as.numeric(z$theta),as.numeric(theta)),"Theta changed before final diagnostics")
    state$newton_checks <- state$newton_checks+1L
  }
  traced <- character()
  on.exit(for(n in rev(traced)) untrace(n,where=ns),add=TRUE)
  for(n in c("phase1.1","phase1.2","phase2.1","proc2subphase","doIterations","maxlikec")) {
    assert(exists(n,envir=ns,inherits=FALSE),paste("Missing guard",n))
    trace(n,tracer=block,print=FALSE,where=ns);traced<-c(traced,n)
  }
  trace("phase3",tracer=substitute(CHECK(z,x),list(CHECK=enter)),print=FALSE,where=ns);traced<-c(traced,"phase3")
  trace("simstats0c",tracer=substitute(CHECK(z,fromFiniteDiff),list(CHECK=simulation)),print=FALSE,where=ns);traced<-c(traced,"simstats0c")
  trace("PotentialNR",tracer=substitute(CHECK(z,x,MakeStep),list(CHECK=newton)),print=FALSE,where=ns);traced<-c(traced,"PotentialNR")
  started <- proc.time();record("starting")
  fresh <- tryCatch(withCallingHandlers(
    siena07(algorithm,data=netdata,effects=bound$effects,prevAns=NULL,batch=TRUE,
      silent=TRUE,useCluster=FALSE,returnDeps=FALSE),
    warning=function(w) {state$warnings<-c(state$warnings,conditionMessage(w))}),
    error=function(e) {record("failed",conditionMessage(e));stop(e)})
  elapsed <- unname((proc.time()-started)[3])
  # Save the native return before further validation, including invalid diagnostics.
  saveRDS(fresh,file.path(out,"diagnostic-fit.rds"))
  assert(isTRUE(fresh$OK) && identical(fresh$termination,"OK") && !isTRUE(fresh$Phase3Interrupt),"Native diagnostic incomplete")
  assert(state$simulator_calls==3000L && fresh$Phase3nits==3000L && fresh$n==3000L &&
    identical(dim(fresh$sf),c(3000L,58L)),"Wrong number of completed draws")
  assert(state$forbidden_entries==0L && state$newton_checks==1L,"Native guard count differs")
  assert(identical(as.numeric(fresh$theta),as.numeric(theta)) && identical(original$theta,theta),"Final theta changed")
  assert(identical(as.logical(fresh$fixed),as.logical(original$fixed)),"Final fixed flags changed")
  assert(identical(parameter_keys(fresh$requestedEffects),parameter_keys(original$requestedEffects)),"Final effect identities changed")
  full <- reconstruct_diagnostics(fresh$sf,fresh$fixed)
  prefix <- reconstruct_diagnostics(fresh$sf[1:1000,,drop=FALSE],fresh$fixed)
  assert(same_numbers(full$t_ratios,fresh$tconv) && same_numbers(full$covariance,fresh$msf) &&
    abs(full$overall-fresh$tconv.max)<1e-12,"Fresh diagnostic reconstruction mismatch")
  diagnostic <- function(x,n) list(draws=n,maximum_absolute_t=x$maximum_absolute_t,
    overall=x$overall,individual_pass=x$maximum_absolute_t<0.1,overall_pass=x$overall<0.25)
  saveRDS(fresh$sf,file.path(out,"moment-deviations.rds"))
  write.csv(full$covariance,file.path(out,"moment-covariance.csv"),row.names=FALSE)
  table <- original$requestedEffects[,identity_columns,drop=FALSE]
  table$index<-seq_along(theta);table$theta_before<-theta;table$theta_after<-fresh$theta
  table$observed_target<-fresh$targets;table$mean_deviation<-full$mean;table$t_ratio<-full$t_ratios
  write.csv(table,file.path(out,"parameter-diagnostics.csv"),row.names=FALSE,na="NA")
  native <- fit_diagnostics(fresh,3000L)
  result <- list(status="completed",stage="3B",training_years=1990:2008,actors=161L,
    parameters=58L,draws=3000L,seed=2009301L,nsub=0L,simOnly=FALSE,
    simulator_calls=state$simulator_calls,phase3_entries=state$phase3_entries,
    optimization_entries=state$forbidden_entries,newton_checks=state$newton_checks,
    coefficients_identical_at_every_simulator_call=TRUE,coefficients_identical_after=TRUE,
    fixed_flags_identical=TRUE,observed_targets_identical=TRUE,
    original=diagnostic(old,1000L),fresh_prefix=diagnostic(prefix,1000L),fresh_full=diagnostic(full,3000L),
    historical_fit_accepted=FALSE,fresh_native_diagnostics=native,
    native_elapsed_seconds=elapsed,warnings=state$warnings,source_function_verification=sources,
    reconstruction=list(max_t_error=max(abs(full$t_ratios-fresh$tconv)),
      max_covariance_error=max(abs(full$covariance-fresh$msf)),overall_error=as.numeric(abs(full$overall-fresh$tconv.max))),
    new_refits=0L,new_forecasts=0L,target_packets_read=0L,raw_archives_read=0L,
    interpretation="One new diagnostic batch at unchanged theta. Prefix and full estimates are nested, not independent repetitions. No variability estimate or historical acceptance update; primary fitting policy unchanged.")
  write_json(result,file.path(out,"result.json"),auto_unbox=TRUE,pretty=TRUE,na="null",null="null",digits=17)
  writeLines(capture.output(sessionInfo()),file.path(out,"session-info.txt"))
  record("completed");result
}

args <- commandArgs(trailingOnly=TRUE)
if(identical(args,"--self-test")) {
  cat(toJSON(pilot_self_test(),auto_unbox=TRUE,pretty=TRUE),"\n")
} else {
  assert(length(args)==3L && args[1]=="--execute-one-pilot","Use --self-test or --execute-one-pilot ROOT OUTPUT")
  cat(toJSON(run_pilot(normalizePath(args[2]),normalizePath(args[3])),auto_unbox=TRUE,pretty=TRUE,digits=17),"\n")
}
