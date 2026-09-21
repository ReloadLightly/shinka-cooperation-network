# Step 3B: ONE phase-3-only assessment of the saved 2009 attempt-3 vector.
# This file loads the hash-bound 3A function definitions, never its CLI.
expressions <- parse("R/convergence_preflight.R")
cli_start <- which(vapply(as.list(expressions), function(e)
  is.call(e) && identical(e[[1]], as.name("<-")) &&
  identical(e[[2]], as.name("args")), logical(1)))
stopifnot(length(cli_start) == 1L, cli_start == length(expressions) - 1L)
for (e in as.list(expressions)[seq_len(cli_start - 1L)]) eval(e, .GlobalEnv)

check_simulation_state <- function(z, theta, fromFiniteDiff=FALSE) {
  assert(identical(as.numeric(z$theta), as.numeric(theta)), "Simulator coefficient vector changed")
  assert(z$Phase == 3L && z$pp == 58L, "Unexpected simulation phase or parameter count")
  assert(identical(fromFiniteDiff,FALSE) && identical(z$FinDiff.method,FALSE),
    "Finite differences would perturb the coefficient vector")
  assert(!isTRUE(z$maxlike) && !isTRUE(z$gmm) && !isTRUE(z$cconditional), "Different native method")
  assert(is.null(z$cl) && isTRUE(z$Deriv), "Expected serial score-based phase 3")
}

check_phase3_state <- function(z,x,fit) {
  assert(x$nsub == 0L && x$n3 == 3000L && x$randomSeed == 2009301L &&
    identical(x$simOnly,FALSE), "Unapproved pilot settings")
  assert(z$n == 0L && !isTRUE(z$cconditional), "Optimization or conditioning detected")
  assert(identical(as.numeric(z$theta),as.numeric(fit$theta)), "Initialization changed theta")
  assert(identical(parameter_keys(z$requestedEffects),parameter_keys(fit$requestedEffects)), "Effect ordering changed")
  assert(identical(as.logical(z$fixed),as.logical(fit$fixed)) && !any(z$fixed), "Fixed flags changed")
  assert(same_numbers(z$targets,fit$targets,0) && same_numbers(z$targets2,fit$targets2,0), "Training targets changed")
  assert(z$observations == 19L && z$pp == 58L, "Training scope changed")
}

pilot_self_tests <- function() {
  n <- 0L
  bad <- function(expr) {assert(inherits(try(force(expr),silent=TRUE),"try-error"),"Expected refusal");n<<-n+1L}
  theta <- seq_len(58L)/100
  z <- list(theta=theta,Phase=3L,pp=58L,FinDiff.method=FALSE,maxlike=FALSE,
    gmm=FALSE,cconditional=FALSE,cl=NULL,Deriv=TRUE)
  check_simulation_state(z,theta);n<-n+1L
  moved <- z;moved$theta[2]<-moved$theta[2]+1e-10;bad(check_simulation_state(moved,theta))
  wrong <- z;wrong$Phase<-2L;bad(check_simulation_state(wrong,theta))
  wrong <- z;wrong$FinDiff.method<-TRUE;bad(check_simulation_state(wrong,theta))
  bad(check_simulation_state(z,theta,TRUE))
  wrong <- z;wrong$cconditional<-TRUE;bad(check_simulation_state(wrong,theta))
  wrong <- z;wrong$cl<-list("worker");bad(check_simulation_state(wrong,theta))
  wrong <- z;wrong$Deriv<-FALSE;bad(check_simulation_state(wrong,theta))
  list(status="passed",checks=n,new_simulations=0L)
}

run_pilot <- function(root,output) {
  assert(as.character(getRversion())=="4.2.1" && as.character(packageVersion("RSiena"))=="1.3.10", "Wrong native runtime")
  source_audit <- native_source_check(file.path(root,"vendor/RSiena"))
  tests <- pilot_self_tests()
  policy <- read_json("configs/convergence-preflight-v1.json",simplifyVector=TRUE)
  fit <- readRDS(file.path(root,policy$fit_path))
  packet <- readRDS(file.path(output,"training-packet.rds"))
  assert(identical(as.integer(packet$years),1990:2008) && length(packet$nms)==161L, "Wrong training packet")
  assert(length(fit$theta)==58L && nrow(fit$sf)==1000L && fit$Phase3nits==1000L, "Wrong saved fit")
  old <- fit_diagnostics(fit,1000L)
  assert(identical(old$valid,FALSE) && isTRUE(old$finite_identified), "Historical status changed")
  netdata <- make_training_data(packet)
  bound <- bind_saved_theta(model_effects(netdata),fit)
  x <- prepare_algorithm(fit,file.path(output,"native-pilot"))
  original_theta <- fit$theta
  st <- new.env(parent=emptyenv())
  st$phase3_entries<-0L;st$sim_entries<-0L;st$sim_exits<-0L;st$forbidden<-0L
  st$nr_entries<-0L;st$postprocess_entries<-0L;st$warnings<-character()
  st$started <- proc.time()[[3]]
  audit <- function(status) list(status=status,phase3_entries=st$phase3_entries,
    simulator_entries=st$sim_entries,simulator_exits=st$sim_exits,
    forbidden_entries=st$forbidden,potential_nr_calls=st$nr_entries,
    postprocessing_entries=st$postprocess_entries,
    checked_every_simulator_call=TRUE,seed=2009301L,nsub=0L,n3=3000L,simOnly=FALSE,
    warnings=st$warnings,elapsed_seconds=unname(proc.time()[[3]]-st$started))
  flush_audit <- function(status) write_json(audit(status),file.path(output,"guard-audit.json"),
    auto_unbox=TRUE,pretty=TRUE,digits=17,na="null")
  block <- function() {st$forbidden<-st$forbidden+1L;stop("Optimization/alternative simulator forbidden",call.=FALSE)}
  enter_phase <- function(z,x) {
    st$phase3_entries<-st$phase3_entries+1L
    assert(st$phase3_entries==1L,"Second phase-3 entry forbidden")
    check_phase3_state(z,x,fit);flush_audit("phase3_entered")
  }
  enter_sim <- function(z,fromFiniteDiff) {
    check_simulation_state(z,original_theta,fromFiniteDiff)
    assert(st$phase3_entries==1L && st$sim_entries==st$sim_exits,"Unexpected simulator call sequence")
    st$sim_entries<-st$sim_entries+1L
    assert(st$sim_entries<=3000L,"Pilot simulation budget exceeded")
  }
  exit_sim <- function(z) {
    check_simulation_state(z,original_theta,FALSE)
    st$sim_exits<-st$sim_exits+1L
    if(st$sim_exits %% 250L==0L) {
      flush_audit("running")
      cat(sprintf("STEP3B: %d/3000 draws; theta unchanged; elapsed %.1f s\n",st$sim_exits,proc.time()[[3]]-st$started))
      flush.console()
    }
  }
  before_postprocess <- function(z,x) {
    st$postprocess_entries<-st$postprocess_entries+1L
    assert(st$postprocess_entries==1L && st$sim_exits==3000L,"Incomplete phase-3 draws")
    assert(identical(as.numeric(z$theta),as.numeric(original_theta)),"Theta moved before diagnostics")
    assert(identical(dim(z$sf),c(3000L,58L)) && all(is.finite(z$sf)),"Malformed phase-3 matrix")
    # Preserve the samples before derivative/covariance postprocessing can fail.
    saveRDS(list(sf=z$sf,ssc=z$ssc,sf2=z$sf2,theta=z$theta,targets=z$targets,
      targets2=z$targets2,fixed=z$fixed,requestedEffects=z$requestedEffects),
      file.path(output,"raw-phase3.rds"))
  }
  before_nr <- function(z,x,MakeStep) {
    st$nr_entries<-st$nr_entries+1L
    assert(identical(MakeStep,FALSE),"Newton coefficient adjustment forbidden")
    assert(identical(as.numeric(z$theta),as.numeric(original_theta)),"Theta changed before Newton diagnostic")
  }
  ns<-asNamespace("RSiena");traced<-character()
  on.exit({for(n in rev(traced))untrace(n,where=ns)},add=TRUE)
  add_trace<-function(name,expr,exit=NULL) {
    trace(name,tracer=expr,exit=exit,where=ns,print=FALSE);traced<<-c(traced,name)
  }
  for(n in c("phase1.1","phase1.2","phase2.1","proc2subphase","maxlikec")) add_trace(n,block)
  add_trace("phase3",substitute(F(z,x),list(F=enter_phase)))
  add_trace("simstats0c",substitute(F(z,fromFiniteDiff),list(F=enter_sim)),
    substitute(F(z),list(F=exit_sim)))
  add_trace("phase3.2",substitute(F(z,x),list(F=before_postprocess)))
  add_trace("PotentialNR",substitute(F(z,x,MakeStep),list(F=before_nr)))
  flush_audit("prepared")
  result <- tryCatch(withCallingHandlers(
    siena07(x,data=netdata,effects=bound$effects,prevAns=NULL,batch=TRUE,
      silent=TRUE,useCluster=FALSE,returnDeps=FALSE),
    warning=function(w) {st$warnings<-c(st$warnings,conditionMessage(w))}),
    error=function(e) {flush_audit("failed");stop(e)})
  # Save even a numerically unsuccessful result. Never rerun a seed to get a pass.
  saveRDS(result,file.path(output,"diagnostic.rds"))
  assert(st$sim_entries==3000L && st$sim_exits==3000L && st$forbidden==0L,
    "Pilot did not complete exactly 3000 guarded calls")
  assert(st$nr_entries==1L && st$postprocess_entries==1L,"Unexpected diagnostic path")
  assert(identical(as.numeric(result$theta),as.numeric(original_theta)) &&
    identical(original_theta,fit$theta),"Final coefficient vector changed")
  assert(identical(parameter_keys(result$requestedEffects),parameter_keys(fit$requestedEffects)) &&
    identical(as.logical(result$fixed),as.logical(fit$fixed)),"Final parameter flags/order changed")
  assert(result$n==3000L && result$Phase3nits==3000L && !isTRUE(result$Phase3Interrupt),"Wrong iteration count")
  full <- reconstruct_diagnostics(result$sf,result$fixed)
  first <- reconstruct_diagnostics(result$sf[1:1000,,drop=FALSE],result$fixed)
  assert(same_numbers(full$covariance,result$msf) && same_numbers(full$t_ratios,result$tconv) &&
    abs(full$overall-as.numeric(result$tconv.max))<1e-12,"Native diagnostic reconstruction mismatch")
  native <- fit_diagnostics(result,3000L)
  compact <- function(d,n) list(draws=n,maximum_absolute_t=d$maximum_absolute_t,
    overall=d$overall,individual_pass=d$maximum_absolute_t<0.1,overall_pass=d$overall<0.25)
  write.csv(result$sf,file.path(output,"moment-deviations.csv"),row.names=FALSE)
  write.csv(full$covariance,file.path(output,"moment-covariance.csv"),row.names=FALSE)
  map <- fit$requestedEffects[,identity_columns,drop=FALSE]
  map$theta<-original_theta;map$mean_deviation<-full$mean;map$t_ratio<-full$t_ratios
  write.csv(map,file.path(output,"parameter-diagnostics.csv"),row.names=FALSE,na="NA")
  flush_audit("completed")
  report<-list(status="completed",stage="3B",seed=2009301L,draws=3000L,replications=1L,
    training_years=1990:2008,actors=161L,parameters=58L,nsub=0L,simOnly=FALSE,
    coefficients_identical=TRUE,original_fixed_flags_preserved=TRUE,
    historical_attempt_accepted=FALSE,new_refits=0L,new_forecasts=0L,target_packets_read=0L,
    raw_archives_read=0L,step3c_started=FALSE,guard=audit("completed"),
    original_1000=list(maximum_absolute_t=old$maximum_absolute_t_ratio,overall=old$overall_maximum_convergence),
    fresh_first_1000=compact(first,1000L),fresh_full_3000=compact(full,3000L),
    native_diagnostics=native,source_function_verification=source_audit,self_tests=tests,
    interpretation="One fresh fixed-coefficient diagnostic, not a replication study or change to historical acceptance. First 1000 and full 3000 are nested, correlated subsets; seed and budget both differ from the historical diagnostic. No pure causal precision effect or search readiness is established.")
  write_json(report,file.path(output,"summary.json"),auto_unbox=TRUE,pretty=TRUE,digits=17,na="null")
  writeLines(capture.output(sessionInfo()),file.path(output,"session-info.txt"))
  report
}

if(sys.nframe()==0L) {
  args<-commandArgs(trailingOnly=TRUE)
  if(identical(args,"--self-test")) cat(toJSON(pilot_self_tests(),auto_unbox=TRUE),"\n")
  else {
    assert(length(args)==3L && args[1]=="--execute-one-pilot","Expected --execute-one-pilot ROOT OUTPUT")
    report<-run_pilot(normalizePath(args[2]),normalizePath(args[3]))
    cat(toJSON(report,auto_unbox=TRUE,pretty=TRUE,digits=17),"\n")
  }
}
