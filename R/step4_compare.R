# Step 4: one fixed mechanism comparison, using explicit precision acceptance.
# Historical estimator, forecast and scorer files are never edited.
source("R/precision_convergence.R")
STEP4_VERSION <- "step4-closure-comparison-v1"
step4_plan <- function() read_json("configs/step4-comparison-v1.json",simplifyVector=FALSE)
step4_seed <- function(year,model,batch) {
  assert(year%in%2006:2009&&model%in%c("reference","gwesp69")&&batch%in%1:5,"Undeclared forecast cell")
  as.integer(61000000+100*year+10*match(model,c("reference","gwesp69"))-10+batch)
}
step4_receipt <- function(path,effects=NULL) {
  ans<-readRDS(path)
  assert(identical(ans$convergence_policy,PRECISION_VERSION)&&ans$accepted_attempt%in%1:4&&
    ans$authoritative_n3%in%c(1000L,3000L),"Missing explicit precision acceptance")
  d<-fit_diagnostics(ans$fit,ans$authoritative_n3)
  assert(isTRUE(d$valid)&&identical(d,ans$authoritative_diagnostics),"Receipt diagnostics or actual n3 disagree")
  assert(tail(ans$diagnostics,1)[[1]]$attempt==ans$accepted_attempt,"Receipt history ends at wrong attempt")
  if(!is.null(effects)) v2_update_theta(effects,ans$fit)
  ans
}
step4_imported_fit <- function(entry,netdata,effects,spec,settings,attempt,previous=NULL,check_previous=TRUE) {
  assert(identical(precision_sha(entry$path),entry$sha256),"Archived checkpoint hash differs")
  original<-readRDS(entry$path)
  assert(inherits(original,"sienaFit"),"Optimization history must contain native fit objects")
  schedule<-fit_schedule(settings,attempt)
  assert(original$x$nsub==schedule$nsub&&original$x$n3==schedule$n3&&
    original$x$randomSeed==settings$estimation$seed+attempt-1L,"Archived optimizer schedule differs")
  for(k in c("maxlike","gmm","simOnly","cconditional","useStdInits","FinDiff.method"))
    assert(identical(original$x[[k]],FALSE),paste("Archived algorithm differs",k))
  assert(identical(unname(original$x$modelType),3)&&identical(unname(original$x$behModelType),1),"Archived model type differs")
  tagged<-v2_adopt_legacy_fit(original,effects,spec)
  bound<-bind_saved_theta(effects,tagged)
  assert(identical(tagged$theta,original$theta),"Import changed coefficients")
  if(check_previous&&attempt>1L) {
    assert(!is.null(previous)&&!is.null(entry$previous_path),"Missing original continuation history")
    prior<-readRDS(entry$previous_path)
    for(k in c("theta","dfra","dinv","sf","regrCoef","regrCor","fixed","maxlike"))
      assert(identical(previous[[k]],prior[[k]]),paste("Imported continuation input differs",k))
  }
  tagged
}
step4_fit <- function(cell,packet_path,model,year) {
  req<-read_json(file.path(cell,"request.json"),simplifyVector=FALSE)
  spec<-validate_network_specification_v2(req$specification)
  settings<-read_json("configs/precision-fit-v1.json",simplifyVector=TRUE);precision_policy(settings)
  packet<-readRDS(packet_path)
  assert(identical(as.integer(packet$years),1990:(year-1L)),"Wrong training history")
  train<-make_training_data(packet);effects<-build_network_effects_v2(train,spec)$effects
  out<-file.path(cell,"fit");dir.create(out,showWarnings=FALSE)
  if(!file.exists(file.path(out,"request.json")))precision_json(req,file.path(out,"request.json"))
  imports<-req$import_history$attempts
  imported<-list();new_calls<-0L
  optimizer<-function(netdata,effs,settings,outdir,attempt,previous) {
    entry<-imports[[as.character(attempt)]]
    if(!is.null(entry)) {
      value<-step4_imported_fit(entry,netdata,effs,spec,settings,attempt,previous)
      imported[[as.character(attempt)]]<<-list(source=entry$path,sha256=entry$sha256,
        original_acceptance_imported=FALSE,coefficient_change=FALSE)
      cat("STEP4 immutable optimization checkpoint",attempt,"reused; policy decision still pending\n");flush.console()
      return(value)
    }
    new_calls<<-new_calls+1L
    cat("STEP4 new optimization attempt",attempt,"\n");flush.console()
    precision_optimizer(netdata,effs,settings,outdir,attempt,previous)
  }
  ans<-fit_model_precision(train,effects,settings,out,year,optimizer=optimizer)
  checked<-step4_receipt(file.path(out,"accepted_fit.rds"),effects)
  record<-list(status="accepted",version=PRECISION_VERSION,target=year,
    accepted_attempt=ans$accepted_attempt,authoritative_n3=ans$authoritative_n3,
    diagnostics=ans$authoritative_diagnostics,new_forecasts=0L,targets_read=0L)
  if(!file.exists(file.path(out,"accepted.json")))precision_json(record,file.path(out,"accepted.json"))
  audit<-list(version=STEP4_VERSION,status="accepted",model=model,target=year,
    imported_optimization_checkpoints=imported,new_optimization_calls_this_invocation=new_calls,
    authoritative_n3=ans$authoritative_n3,accepted_attempt=ans$accepted_attempt,
    historical_acceptance_imported=FALSE,forecasts=0L,target_reads=0L)
  precision_json(audit,file.path(cell,"fit-audit.json"));audit
}

# Private lexical adapter: reuse unchanged forward semantics, but validate the
# new receipt using its actual authoritative_n3, never the old attempt schedule.
step4_forward <- function(cell,packet_path,model,year,batch,verify_only=FALSE) {
  fitpath<-file.path(cell,"fit","accepted_fit.rds")
  receipt_sha<-precision_sha(fitpath);ans<-step4_receipt(fitpath)
  out<-file.path(cell,"forecasts",as.character(batch));dir.create(out,recursive=TRUE,showWarnings=FALSE)
  settings<-read_json("configs/precision-fit-v1.json",simplifyVector=TRUE)
  settings$forecast$seed_override<-step4_seed(year,model,batch)
  specfile<-file.path(cell,"specification.json")
  settingsfile<-file.path(out,"forecast-settings.json")
  if(!file.exists(settingsfile))precision_json(settings,settingsfile)
  scope<-new.env(parent=environment(run_forecast_multiobjective))
  original_read<-readRDS
  scope$readRDS<-function(file,...) {
    if(identical(normalizePath(file,mustWork=FALSE),normalizePath(file.path(out,"accepted_fit.rds"),mustWork=FALSE)))return(ans)
    original_read(file,...)
  }
  original_exists<-file.exists
  scope$file.exists<-function(...) {
    paths<-c(...)
    if(length(paths)==1L&&identical(paths,file.path(out,"accepted_fit.rds")))TRUE else original_exists(...)
  }
  scope$fit_schedule<-function(settings,attempt) {
    assert(attempt==ans$accepted_attempt,"Old schedule attempted to infer authoritative n3")
    list(nsub=0L,n3=ans$authoritative_n3)
  }
  scope$fit_model_v2<-function(...)stop("Forecast process may not estimate a model")
  native<-v2_native_runner();native_calls<-0L;capture<-NULL
  scope$v2_native_runner<-function() function(x,data,effects,...) {
    native_calls<<-native_calls+1L
    assert(native_calls==1L&&x$nsub==0L&&x$n3==1000L&&isTRUE(x$simOnly)&&
      x$randomSeed==step4_seed(year,model,batch)&&all(effects$fix[effects$include]),"Wrong fixed forecast route")
    expected<-effects[effects$include,,drop=FALSE]
    expected<-do.call(rbind,lapply(unique(expected$name),function(n)expected[expected$name==n,,drop=FALSE]))
    capture<<-list(theta=as.numeric(expected$initialValue),keys=parameter_keys(expected),fixed=as.logical(expected$fix))
    ns<-asNamespace("RSiena");entered<-0L;exited<-0L
    check<-function(z){assert(identical(as.numeric(z$theta),capture$theta),"Forecast theta changed")}
    enter<-function(z,fromFiniteDiff){check(z);assert(z$Phase==3L&&identical(fromFiniteDiff,FALSE),"Unexpected forecast phase");entered<<-entered+1L}
    leave<-function(z){check(z);exited<<-exited+1L}
    phase<-function(z,x) {
      check(z);assert(identical(parameter_keys(z$requestedEffects),capture$keys)&&all(z$fixed),"Forecast identities differ")
      if(verify_only)stop(structure(list(message="Verified forecast initialization; no simulation",call=NULL),class=c("step4_stop","error","condition")))
    }
    traced<-character();on.exit(for(n in rev(traced))untrace(n,where=ns),add=TRUE)
    add<-function(n,expr,exit=NULL){trace(n,tracer=expr,exit=exit,where=ns,print=FALSE);traced<<-c(traced,n)}
    for(n in c("phase1.1","phase1.2","phase2.1","proc2subphase","maxlikec"))add(n,function()stop("Forecast optimization forbidden"))
    add("phase3",substitute(F(z,x),list(F=phase)))
    add("simstats0c",substitute(F(z,fromFiniteDiff),list(F=enter)),substitute(F(z),list(F=leave)))
    value<-native(x,data=data,effects=effects,...)
    check(value);assert(entered==1000L&&exited==1000L,"Forecast endpoint guard count differs")
    value
  }
  scope$saveRDS<-function(object,file,...)base::saveRDS(object,file,compress="xz",version=2)
  forward<-run_forecast_multiobjective;environment(forward)<-scope
  outcome<-tryCatch(forward(specfile,year,out,settingsfile,packet_path),step4_stop=function(e)e)
  assert(precision_sha(fitpath)==receipt_sha,"Forecast rewrote accepted fit")
  if(verify_only){assert(inherits(outcome,"step4_stop")&&native_calls==1L,"Expected forecast preflight stop missing");return(list(status="verified_without_simulation",authoritative_n3=ans$authoritative_n3))}
  assert(native_calls==1L,"Forecast did not use exactly one native call")
  audit<-list(status="complete",version=STEP4_VERSION,model=model,target=year,batch=batch,
    seed=step4_seed(year,model,batch),simulations=1000L,fit_sha256=receipt_sha,
    accepted_attempt=ans$accepted_attempt,authoritative_n3=ans$authoritative_n3,
    all_forward_coefficients_fixed=TRUE,coefficients_checked_each_call=TRUE,
    new_estimation_calls=0L,target_reads=0L)
  precision_json(audit,file.path(out,"receipt-audit.json"));audit
}
step4_pool <- function(cell) {
  predictions<-lapply(1:5,function(b)readRDS(file.path(cell,"forecasts",b,"predictions.rds")))
  fields<-setdiff(names(predictions[[1]]),c("probabilities","behavior_mean","seed","simulations"))
  for(p in predictions)for(k in fields)assert(identical(p[[k]],predictions[[1]][[k]]),paste("Batch scope differs",k))
  combine<-function(indices){p<-predictions[[1]];p$probabilities<-Reduce(`+`,lapply(predictions[indices],`[[`,"probabilities"))/length(indices)
    p$behavior_mean<-Reduce(`+`,lapply(predictions[indices],`[[`,"behavior_mean"))/length(indices)
    p$simulations<-1000L*length(indices);p$seed<-NULL;p$batch_seeds<-vapply(predictions[indices],`[[`,integer(1),"seed");p}
  out<-file.path(cell,"pooled");dir.create(out,showWarnings=FALSE)
  precision_save(combine(1:5),file.path(out,"predictions.rds"))
  for(b in 1:5)precision_save(combine(setdiff(1:5,b)),file.path(out,paste0("delete-",b,".rds")))
  list(status="predictions_committed_before_scoring",endpoints=5000L,delete_one_blocks=5L)
}
# Only this separate R process reads development outcomes. The original scorer
# is used verbatim for each 1000-endpoint batch; pooled metrics use its functions
# and the identical saved eligibility mask, not a new dyad-selection rule.
step4_score <- function(cell,target_path) {
  source("R/score.R")
  scores<-lapply(1:5,function(b){out<-file.path(cell,"scores",b);score_forecast(file.path(cell,"forecasts",b,"predictions.rds"),target_path,out)})
  truth<-readRDS(target_path);first<-readRDS(file.path(cell,"forecasts",1,"predictions.rds"))
  mask<-readRDS(file.path(cell,"scores",1,"eligibility_mask.rds"))
  for(b in 2:5)assert(identical(mask,readRDS(file.path(cell,"scores",b,"eligibility_mask.rds"))),"Repeated forecast mask differs")
  ix<-match(as.character(first$nms),as.character(truth$nms));n<-length(ix);present<-!is.na(ix)
  present[present]<-as.logical(truth$present[ix[present]])
  y<-matrix(NA_real_,n,n);beh<-rep(NA_real_,n);known<-which(!is.na(ix))
  y[known,known]<-truth$network[ix[known],ix[known]];beh[known]<-truth$behavior[ix[known]]
  bmask<-as.logical(first$origin_active)&present&is.finite(beh)
  metric<-function(p){assert(identical(p$origin_active,first$origin_active)&&identical(p$nms,first$nms),"Pooled scope differs")
    prob<-p$probabilities[mask];labels<-y[mask];origin<-first$origin_network[mask]
    assert(all(is.finite(p$behavior_mean))&&all(p$behavior_mean>=1&p$behavior_mean<=11),"Pooled behavior invalid")
    list(pr_auc=curve_metrics(prob,labels)$pr_auc,brier=mean((prob-labels)^2),
      spending_rmse=sqrt(mean((p$behavior_mean[bmask]-beh[bmask])^2)),
      formation_pr_auc=curve_metrics(prob[origin==0],labels[origin==0])$pr_auc,
      dissolution_pr_auc=curve_metrics(1-prob[origin==1],1-labels[origin==1])$pr_auc)}
  pooled<-metric(readRDS(file.path(cell,"pooled","predictions.rds")))
  deletion<-lapply(1:5,function(b)metric(readRDS(file.path(cell,"pooled",paste0("delete-",b,".rds")))))
  summary<-list(status="complete",pooled=pooled,delete_one_batch=deletion,
    batches=lapply(scores,function(s)list(pr_auc=s$primary$pr_auc,brier=s$primary$brier,spending_rmse=s$spending$rmse,
      formation_pr_auc=s$formation$pr_auc,dissolution_pr_auc=s$dissolution$pr_auc)),
    eligibility_sha256=precision_sha(file.path(cell,"scores",1,"eligibility_mask.rds")),
    dyads=sum(mask),spending_countries=sum(bmask),primary_endpoints=5000L,
    uncertainty="Conditional simulation precision only; five-block jackknife is approximate, especially for PR-AUC ties",
    structural_checks=lapply(scores,`[[`,"structural_predictive_checks"))
  precision_json(summary,file.path(cell,"scores","comparison-metrics.json"));summary
}

if(sys.nframe()==0L){
  args<-commandArgs(trailingOnly=TRUE);mode<-args[1]
  assert(as.character(getRversion())=="4.2.1"&&as.character(packageVersion("RSiena"))=="1.3.10","Wrong native versions")
  if(mode=="fit") step4_fit(args[2],args[3],args[4],as.integer(args[5]))
  else if(mode=="forecast") step4_forward(args[2],args[3],args[4],as.integer(args[5]),as.integer(args[6]))
  else if(mode=="pool")step4_pool(args[2])
  else if(mode=="score")step4_score(args[2],args[3])
  else stop("Use the explicit Python Step 4 orchestrator")
}
