# Opt-in estimator. Historical model/forecast/scoring sources remain unmodified.
source("R/forecast_multiobjective.R")
# Import audited 3A functions without entering its command-line program.
.precision_expr <- as.list(parse("R/convergence_preflight.R"))
.precision_stop <- which(vapply(.precision_expr,function(e)
  is.call(e)&&identical(e[[1]],as.name("<-"))&&identical(e[[2]],as.name("args")),logical(1)))
stopifnot(length(.precision_stop)==1L)
for(e in .precision_expr[seq_len(.precision_stop-1L)]) eval(e,.GlobalEnv)
rm(.precision_expr,.precision_stop)

PRECISION_VERSION <- "precision-before-continuation-v1"
precision_sha <- function(path) {
  value <- system2("sha256sum",shQuote(normalizePath(path,mustWork=TRUE)),stdout=TRUE)
  assert(is.null(attr(value,"status"))&&length(value)==1L,"SHA256 calculation failed")
  substr(value,1,64)
}
precision_object_sha <- function(x) {
  f<-tempfile();on.exit(unlink(f),add=TRUE)
  saveRDS(x,f,compress=FALSE,version=2);precision_sha(f)
}
precision_save <- function(value,path) {
  # Atomic no-replacement publication. Failed operations remain visible.
  pending<-paste0(path,".pending-",Sys.getpid())
  on.exit(unlink(pending),add=TRUE)
  saveRDS(value,pending,compress="xz",version=2)
  assert(file.link(pending,path),paste("Refusing to replace evidence",path))
}
precision_json <- function(value,path) {
  assert(!file.exists(path),paste("Refusing to replace evidence",path))
  write_json(value,path,auto_unbox=TRUE,pretty=TRUE,digits=17,null="null",na="null")
}
precision_policy <- function(settings) {
  p<-read_json("configs/convergence-assessment-v1.json",simplifyVector=TRUE)
  old<-read_json("configs/evaluator-v2.json",simplifyVector=TRUE)
  check<-settings;check$version<-old$version;check$estimation$convergence_assessment<-NULL
  assert(identical(check,old),"Precision profile may not change the original science/settings")
  assert(identical(settings$version,"precision-fit-v1")&&
    identical(settings$estimation$convergence_assessment,PRECISION_VERSION)&&
    identical(p$version,PRECISION_VERSION)&&p$diagnostic_draws==3000L&&p$nsub==0L&&
    identical(p$simOnly,FALSE)&&isTRUE(p$serial)&&p$seed_base==52000000&&
    p$individual_strictly_below==0.1&&p$overall_strictly_below==0.25&&
    p$maximum_assessments_per_unchanged_vector==1L&&p$maximum_extra_assessments_per_fit==3L,
    "Unknown or altered precision policy")
  p
}
precision_seed <- function(target,attempt) {
  assert(length(target)==1L&&is.finite(target)&&target%in%2006:2009&&
    length(attempt)==1L&&is.finite(attempt)&&attempt%in%1:4,"Invalid development target/attempt")
  as.integer(52000000+10*target+attempt)
}
precision_action <- function(d,n3) {
  assert(n3%in%c(1000L,3000L),"Unexpected phase-3 budget")
  flags_ok<-all(vapply(c("divergence","fixed_parameters","newly_fixed_parameters"),function(k)
    isTRUE(d[[k]]$shape_valid)&&identical(d[[k]]$any,FALSE),logical(1)))
  eligible<-isTRUE(d$native_ok)&&identical(d$termination,"OK")&&isTRUE(d$phase3_complete)&&
    identical(as.integer(d$phase3_iterations),as.integer(n3))&&isTRUE(d$finite_identified)&&
    isTRUE(d$covariance_all_finite)&&identical(d$covariance_message,"")&&flags_ok&&
    length(d$maximum_absolute_t_ratio)==1L&&is.finite(d$maximum_absolute_t_ratio)&&
    length(d$overall_maximum_convergence)==1L&&is.finite(d$overall_maximum_convergence)
  pass<-eligible&&d$maximum_absolute_t_ratio<0.1&&d$overall_maximum_convergence<0.25
  assert(identical(isTRUE(d$valid),isTRUE(pass)),"Inconsistent native acceptance flags")
  if(pass)"accept_original" else if(eligible&&n3==1000L)"assess_once" else "continue_original"
}
precision_algorithm <- function(fit,prefix,seed) {
  x<-fit$x
  assert(inherits(x,"sienaAlgorithm")&&identical(x$FRANname,"simstats0c"),"Wrong saved algorithm")
  for(k in c("maxlike","gmm","simOnly","cconditional","useStdInits","FinDiff.method"))
    assert(identical(x[[k]],FALSE),paste("Unsupported algorithm flag",k))
  x$nsub<-0L;x$n3<-3000L;x$randomSeed<-as.integer(seed);x$projname<-prefix;x$FRAN<-"simstats0c"
  x
}
precision_vector_key <- function(fit) {
  x<-fit$x;x[c("nsub","n3","randomSeed","projname","FRAN")]<-NULL
  precision_object_sha(list(theta=as.numeric(fit$theta),identity=parameter_keys(fit$requestedEffects),
    fixed=fit$fixed,test=fit$requestedEffects$test,algorithm=x))
}

# Same phase-3 guards as the verified study, generalized to the supplied model's
# dimension and historical wave count. No 58-parameter limit is introduced.
precision_native_assessment <- function(fit,netdata,effs,seed,folder,verify_only=FALSE) {
  ns<-asNamespace("RSiena");state<-new.env(parent=emptyenv())
  state$entries<-0L;state$exits<-0L;state$phases<-0L;state$nr<-0L
  state$forbidden<-0L;state$warnings<-character();state$start<-proc.time()[3]
  p<-length(fit$theta);theta<-as.numeric(fit$theta)
  bound<-bind_saved_theta(effs,fit)
  x<-precision_algorithm(fit,file.path(folder,"native"),seed)
  snapshot<-function(status)list(status=status,seed=seed,draws=3000L,simulator_entries=state$entries,
    simulator_exits=state$exits,phase3_entries=state$phases,potential_nr_calls=state$nr,
    forbidden_entries=state$forbidden,parameters=p,coefficients_checked_each_call=TRUE,
    nsub=0L,simOnly=FALSE,warnings=state$warnings,elapsed_seconds=unname(proc.time()[3]-state$start))
  flush<-function(status)write_json(snapshot(status),file.path(folder,"guard-audit.json"),
    auto_unbox=TRUE,pretty=TRUE,digits=17,na="null")
  block<-function(){state$forbidden<-state$forbidden+1L;stop("Optimization forbidden in precision assessment")}
  check_theta<-function(z)assert(identical(as.numeric(z$theta),theta),"Precision assessment moved theta")
  phase<-function(z,x){
    state$phases<-state$phases+1L
    assert(state$phases==1L&&z$n==0L&&x$nsub==0L&&x$n3==3000L&&
      identical(x$simOnly,FALSE)&&x$randomSeed==seed,"Wrong precision route")
    check_theta(z)
    assert(identical(parameter_keys(z$requestedEffects),parameter_keys(fit$requestedEffects))&&
      identical(as.logical(z$fixed),as.logical(fit$fixed)),"Precision identity/flags differ")
    assert(same_numbers(z$targets,fit$targets,0)&&same_numbers(z$targets2,fit$targets2,0),"Observed training statistics differ")
    assert(z$pp==p&&z$observations==fit$observations,"Precision training dimension differs")
    flush("phase3_entered")
    if(isTRUE(verify_only))stop(structure(list(message="Expected stop before phase 3",call=NULL),
      class=c("precision_initialization_stop","error","condition")))
  }
  enter<-function(z,fromFiniteDiff){
    check_theta(z)
    assert(z$Phase==3L&&z$pp==p&&identical(fromFiniteDiff,FALSE)&&
      identical(z$FinDiff.method,FALSE)&&is.null(z$cl)&&isTRUE(z$Deriv)&&
      !isTRUE(z$maxlike)&&!isTRUE(z$gmm)&&!isTRUE(z$cconditional),"Wrong simulator mode")
    assert(state$entries==state$exits,"Unexpected nested simulator calls")
    state$entries<-state$entries+1L;assert(state$entries<=3000L,"Precision budget exceeded")
  }
  leave<-function(z){check_theta(z);state$exits<-state$exits+1L
    if(state$exits%%250L==0L){flush("running");cat("PRECISION",state$exits,"/3000; theta unchanged\n");flush.console()}}
  raw<-function(z,x){
    check_theta(z);assert(state$exits==3000L&&identical(dim(z$sf),c(3000L,p)),"Incomplete precision samples")
    precision_save(list(sf=z$sf,ssc=z$ssc,sf2=z$sf2,theta=z$theta,fixed=z$fixed,
      targets=z$targets,targets2=z$targets2,requestedEffects=z$requestedEffects),file.path(folder,"raw-phase3.rds"))
  }
  nr<-function(z,x,MakeStep){check_theta(z);state$nr<-state$nr+1L;assert(identical(MakeStep,FALSE),"Newton update forbidden")}
  traced<-character();on.exit(for(n in rev(traced))untrace(n,where=ns),add=TRUE)
  add<-function(n,e,exit=NULL){trace(n,tracer=e,exit=exit,where=ns,print=FALSE);traced<<-c(traced,n)}
  for(n in c("phase1.1","phase1.2","phase2.1","proc2subphase","maxlikec"))add(n,block)
  add("phase3",substitute(F(z,x),list(F=phase)))
  add("simstats0c",substitute(F(z,fromFiniteDiff),list(F=enter)),substitute(F(z),list(F=leave)))
  add("phase3.2",substitute(F(z,x),list(F=raw)))
  add("PotentialNR",substitute(F(z,x,MakeStep),list(F=nr)))
  flush("prepared")
  result<-tryCatch(withCallingHandlers(v2_native_runner()(x,data=netdata,effects=bound$effects,
    prevAns=NULL,batch=TRUE,silent=TRUE,useCluster=FALSE,returnDeps=FALSE),
    warning=function(w)state$warnings<-c(state$warnings,conditionMessage(w))),
    precision_initialization_stop=function(e)e,
    error=function(e){flush("failed");stop(e)})
  if(inherits(result,"precision_initialization_stop")){
    assert(isTRUE(verify_only)&&state$entries==0L&&state$forbidden==0L,"Invalid stopped initialization")
    flush("initialization_verified_no_simulation")
    return(list(status="initialization_verified_no_simulation",parameters=p,seed=seed,
      coefficients_identical=TRUE,new_simulations=0L,optimization_iterations=0L))
  }
  # Preserve even an unsuccessful native numerical result before validation.
  precision_save(result,file.path(folder,"native-result.rds"))
  assert(state$entries==3000L&&state$exits==3000L&&state$forbidden==0L&&state$nr==1L,
    "Incomplete precision execution or forbidden coefficient work")
  check_theta(result)
  assert(identical(parameter_keys(result$requestedEffects),parameter_keys(fit$requestedEffects))&&
    identical(as.logical(result$fixed),as.logical(fit$fixed)),"Final precision identity/flags differ")
  flush("completed")
  result
}

precision_verify_operation <- function(folder) {
  done<-file.path(folder,"complete.rds")
  assert(file.exists(done),paste("Incomplete operation preserved; no automatic retry:",folder))
  meta<-readRDS(done)
  for(n in names(meta$files))assert(identical(precision_sha(file.path(folder,n)),meta$files[[n]]),paste("Changed operation evidence",n))
  meta
}
precision_assess_once <- function(fit,netdata,effs,target,attempt,outdir,
                                  assessor=precision_native_assessment) {
  key<-precision_vector_key(fit);folder<-file.path(outdir,"precision",key)
  if(dir.exists(folder)){
    meta<-precision_verify_operation(folder)
    assert(identical(meta$vector_key,key),"Precision vector identity mismatch")
    result<-readRDS(file.path(folder,"result.rds"))
    assert(identical(meta$version,PRECISION_VERSION)&&meta$seed==precision_seed(target,meta$attempt)&&
      identical(fit_diagnostics(result,3000L),meta$diagnostics)&&
      identical(as.numeric(result$theta),as.numeric(fit$theta))&&
      identical(parameter_keys(result$requestedEffects),parameter_keys(fit$requestedEffects)),
      "Cached precision decision or coefficient identity changed")
    return(list(fit=result,metadata=meta,reused=TRUE))
  }
  v2_checkpoint_boundary(outdir,"precision_assessment",attempt)
  assert(dir.create(folder,recursive=TRUE),"Cannot reserve precision operation")
  seed<-precision_seed(target,attempt)
  precision_save(list(version=PRECISION_VERSION,vector_key=key,seed=seed,attempt=attempt,
    target=target,n3=3000L,nsub=0L,source_fit_theta=as.numeric(fit$theta)),file.path(folder,"started.rds"))
  result<-assessor(fit,netdata,effs,seed,folder)
  assert(identical(as.numeric(result$theta),as.numeric(fit$theta)),"Assessor returned changed coefficients")
  assert(identical(parameter_keys(result$requestedEffects),parameter_keys(fit$requestedEffects))&&
    identical(as.logical(result$fixed),as.logical(fit$fixed)),"Assessor changed parameter identity/flags")
  d<-fit_diagnostics(result,3000L)
  precision_save(result,file.path(folder,"result.rds"))
  precision_json(d,file.path(folder,"diagnostics.json"))
  names<-list.files(folder);names<-names[!dir.exists(file.path(folder,names))]
  meta<-list(version=PRECISION_VERSION,vector_key=key,seed=seed,attempt=attempt,
    diagnostics=d,n3=3000L,files=setNames(lapply(names,function(n)precision_sha(file.path(folder,n))),names))
  precision_save(meta,file.path(folder,"complete.rds"))
  list(fit=result,metadata=meta,reused=FALSE)
}

precision_optimizer <- function(netdata,effs,settings,outdir,attempt,previous) {
  s<-fit_schedule(settings,attempt)
  x<-sienaAlgorithmCreate(projname=file.path(outdir,paste0("fit-",attempt)),nsub=s$nsub,n3=s$n3,
    seed=settings$estimation$seed+attempt-1L,modelType=c(dv.net=3),behModelType=c(milex.beh=1),cond=FALSE)
  v2_native_runner()(x,data=netdata,effects=effs,prevAns=previous,batch=TRUE,silent=TRUE,
    useCluster=FALSE,returnDeps=FALSE)
}

fit_model_precision <- function(netdata,effs,settings,outdir,target,
                                optimizer=precision_optimizer,assessor=precision_native_assessment) {
  precision_policy(settings);previous<-NULL;history<-list()
  assert(file.exists(file.path(outdir,"request.json")),"Precision estimator requires its explicit bound Python request")
  for(attempt in seq_len(settings$estimation$max_attempts)){
    s<-fit_schedule(settings,attempt);folder<-file.path(outdir,paste0("optimization-",attempt))
    if(dir.exists(folder)){
      meta<-precision_verify_operation(folder)
      assert(meta$attempt==attempt&&meta$nsub==s$nsub&&meta$n3==s$n3&&
        meta$seed==settings$estimation$seed+attempt-1L,"Cached optimizer schedule differs")
      fit<-readRDS(file.path(folder,"fit.rds"))
    }else{
      v2_checkpoint_boundary(outdir,if(attempt==1L)"fit"else"fit_continuation",attempt)
      assert(dir.create(folder),"Cannot reserve optimization operation")
      precision_save(list(attempt=attempt,schedule=s,seed=settings$estimation$seed+attempt-1L),file.path(folder,"started.rds"))
      t<-proc.time()[3];fit<-optimizer(netdata,effs,settings,outdir,attempt,previous)
      precision_save(fit,file.path(folder,"fit.rds"))
      meta<-list(attempt=attempt,nsub=s$nsub,n3=s$n3,seed=settings$estimation$seed+attempt-1L,
        elapsed_seconds=unname(proc.time()[3]-t),files=list(fit.rds=precision_sha(file.path(folder,"fit.rds")),
          started.rds=precision_sha(file.path(folder,"started.rds"))))
      precision_save(meta,file.path(folder,"complete.rds"))
    }
    d<-fit_diagnostics(fit,s$n3);action<-precision_action(d,s$n3)
    record<-list(attempt=attempt,optimization=meta,original_diagnostics=d,action=action)
    selected<-fit;authoritative<-d;actual_n3<-s$n3
    if(action=="assess_once"){
      assessed<-precision_assess_once(fit,netdata,effs,target,attempt,outdir,assessor)
      record$assessment<-assessed$metadata;record$reused_same_vector<-assessed$reused
      authoritative<-assessed$metadata$diagnostics
      if(isTRUE(authoritative$valid)){selected<-assessed$fit;actual_n3<-3000L}
    }
    record$accepted<-isTRUE(authoritative$valid);history[[attempt]]<-record
    # A failed precision assessment never replaces the original continuation input.
    if(record$accepted){
      ans<-list(fit=selected,diagnostics=history,convergence_policy=PRECISION_VERSION,
        accepted_attempt=attempt,authoritative_n3=actual_n3,authoritative_diagnostics=authoritative)
      if(!file.exists(file.path(outdir,"accepted_fit.rds")))precision_save(ans,file.path(outdir,"accepted_fit.rds"))
      return(ans)
    }
    previous<-fit
  }
  stop("Precision policy exhausted the unchanged optimization schedule; no fitness assigned",call.=FALSE)
}

precision_main <- function(root,outdir,specfile,pastfile,target,settingsfile) {
  assert(as.character(getRversion())=="4.2.1"&&as.character(packageVersion("RSiena"))=="1.3.10","Wrong pinned runtime")
  native_source_check(file.path(root,"vendor/RSiena"))
  settings<-read_json(settingsfile,simplifyVector=TRUE);precision_policy(settings)
  assert(target%in%2006:2009,"This preparation entry point is development-only")
  packet<-readRDS(pastfile)
  assert(identical(as.integer(packet$years),1990:(target-1L))&&length(packet$nms)==161L,"Training scope differs")
  spec<-validate_network_specification_v2(read_json(specfile,simplifyVector=FALSE))
  train<-make_training_data(packet);built<-build_network_effects_v2(train,spec)
  ans<-fit_model_precision(train,built$effects,settings,outdir,target)
  v2_update_theta(built$effects,ans$fit)
  assert(isTRUE(fit_diagnostics(ans$fit,ans$authoritative_n3)$valid),"Final precision fit is not acceptable")
  result<-list(status="accepted",version=PRECISION_VERSION,target=target,
    accepted_attempt=ans$accepted_attempt,authoritative_n3=ans$authoritative_n3,
    diagnostics=ans$authoritative_diagnostics,new_forecasts=0L,targets_read=0L)
  if(!file.exists(file.path(outdir,"accepted.json")))precision_json(result,file.path(outdir,"accepted.json"))
  invisible(result)
}
if(sys.nframe()==0L){
  args<-commandArgs(trailingOnly=TRUE)
  assert(length(args)==7L&&args[1]=="--execute-fit-only","Use scripts/precision_fit.py; no implicit execution")
  precision_main(args[2],args[3],args[4],args[5],as.integer(args[6]),args[7])
}
