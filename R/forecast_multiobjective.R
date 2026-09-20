#!/usr/bin/env Rscript
# UNUSED until explicitly selected by the multiobjective evaluator. This file
# neither replaces nor edits the original reproduction/legacy forecast path.
# Candidates never execute here: the input is a trusted validated JSON model.
source("R/forecast.R")
source("R/network_specification_v2.R")

run_forecast_multiobjective <- function(specfile,target,outdir,settingsfile,
                                      pastfile=NULL,prepare_only=FALSE) {
  dir.create(outdir,recursive=TRUE,showWarnings=FALSE)
  spec<-validate_network_specification_v2(read_json(specfile,simplifyVector=FALSE))
  settings<-read_json(settingsfile,simplifyVector=TRUE)
  if(as.character(packageVersion("RSiena"))!="1.3.10"||settings$software$RSiena!="1.3.10")
    stop("Structured forecasting requires native RSiena 1.3.10")
  if(!target%in%c(settings$development_years,settings$final_test_year))stop("Target outside the declared temporal design")
  if(!identical(settings$forecast$conditional,FALSE)||settings$forecast$duration_years!=1||
     settings$forecast$simulations!=1000L)stop("Structured adapter requires the fixed unconditional one-year 1000-endpoint protocol")
  packet<-readRDS(pastfile %||% file.path("data/past",paste0(target,".rds")))
  if(!identical(as.integer(packet$years),1990:(as.integer(target)-1L)))stop("Training packet does not end at the forecast origin")
  train<-make_training_data(packet)
  built<-build_network_effects_v2(train,spec)
  effs<-built$effects
  write_json(spec,file.path(outdir,"canonical_specification.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
  write.csv(effect_table(effs[effs$include,,drop=FALSE]),file.path(outdir,"training_effects.csv"),row.names=FALSE)
  write.csv(effect_table(effs),file.path(outdir,"native_effect_instance_catalog.csv"),row.names=FALSE)
  adapter<-list(version=NETWORK_SPECIFICATION_VERSION,engine="RSiena 1.3.10",
    source_files=c("R/network_specification_v2.R","R/forecast_multiobjective.R"),
    source_md5=as.list(tools::md5sum(c("R/network_specification_v2.R","R/forecast_multiobjective.R"))),
    kernel_modified=FALSE,installed_namespace_modified=FALSE,
    adaptation="Private lexical copies of native siena07, robmon and initializeFRAN retain native function bodies; only updateTheta resolves to a parameter-and-operand-aware same-model coefficient-transfer helper",
    adaptation_reason="Native 1.3.10 updateTheta excludes parm from its key, conflating parameterized instances with identical short names",
    warm_start_native_derivatives="Retained only after exact requested identity/order agreement",
    evolved_coefficient_policy="All requested structure coefficients estimated jointly with unchanged original empirical controls and spending effects",
    declared_terms=length(spec$network_effects),
    requested_estimated_parameters=sum(effs$include&!effs$fix),
    native_instances=nrow(effs),
    final_year_guard="Trusted Python caller must enforce sealed selection before invoking final-test target; this process opens past-only packets")
  write_json(adapter,file.path(outdir,"structured_adapter.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
  forward<-make_forward_data(packet,train)
  write_json(forward$audit,file.path(outdir,"preflight_audit.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
  if(prepare_only) {
    saveRDS(list(train=train,effects=effs,forward=forward,specification=spec),file.path(outdir,"prepared.rds"))
    return(invisible(TRUE))
  }
  fit_path<-file.path(outdir,"accepted_fit.rds")
  if(file.exists(fit_path)) {
    ans<-readRDS(fit_path)
    ans$fit<-v2_adopt_legacy_fit(ans$fit,effs,spec,file.path(outdir,"accepted_fit.rds.legacy-tagging.json"))
    accepted_attempt<-tail(ans$diagnostics,1)[[1]]$attempt
    if(!fit_diagnostics(ans$fit,fit_schedule(settings,accepted_attempt)$n3)$valid)stop("Cached structured fit is not acceptable")
    # Validate parameter/operand identity and native derivative ordering, even
    # when no new estimation attempt is required.
    v2_update_theta(effs,ans$fit)
  } else {
    ans<-fit_model_v2(train,effs,settings,outdir,spec)
    v2_update_theta(effs,ans$fit)
    saveRDS(ans,paste0(fit_path,".pending"))
    if(!file.rename(paste0(fit_path,".pending"),fit_path))stop("Could not publish accepted structured fit")
  }
  fitted<-ans$fit$requestedEffects
  fitted$estimate<-as.numeric(ans$fit$theta)
  fitted$standard_error<-sqrt(diag(ans$fit$covtheta))
  write.csv(effect_table(fitted),file.path(outdir,"fitted_coefficients.csv"),row.names=FALSE)
  fwd<-forward_effects_v2(forward,train,ans$fit,spec)
  write.csv(effect_table(fwd$effects[fwd$effects$include,,drop=FALSE]),file.path(outdir,"forecast_effects.csv"),row.names=FALSE)
  write_json(list(training_mean=forward$audit$training_behavior_mean,
    scaffold_mean=forward$audit$forward_behavior_mean,delta=fwd$mean_shift,
    rule="Expand each dynamic spending ego/alter factor q_train=q_forward+delta; lower-order terms receive fixed derived coefficients",
    changes=fwd$centering_corrections),file.path(outdir,"forecast_coefficient_transform.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
  seed<-as.integer(target)*1000L+1L
  if(!is.null(settings$forecast$seed_override))seed<-settings$forecast$seed_override
  budget<-as.integer(settings$forecast$simulations)
  # The accepted training fit has been published before this boundary. If the
  # execution window closed while siena07 was running, resume directly here.
  v2_checkpoint_boundary(outdir,"forecast",NULL)
  alg<-sienaAlgorithmCreate(projname=file.path(outdir,"forecast"),cond=FALSE,useStdInits=FALSE,
    nsub=0,n3=budget,seed=seed,modelType=c(dv.net=3),behModelType=c(milex.beh=1),simOnly=TRUE)
  started<-proc.time()
  native_run<-v2_native_runner()
  sim<-native_run(alg,data=forward$netdata,effects=fwd$effects,batch=TRUE,silent=TRUE,
    useCluster=FALSE,returnDeps=TRUE)
  S<-length(sim$sims)
  if(S!=budget)stop("Returned endpoint count ",S," differs from fixed budget ",budget)
  N<-length(packet$nms);sum_network<-matrix(0,N,N);sum_behavior<-numeric(N)
  for(s in seq_len(S)) {
    edges<-sim$sims[[s]][[1]][["dv.net"]][[1]]
    a<-matrix(0,N,N)
    if(length(edges))a[edges[,1:2,drop=FALSE]]<-edges[,3]
    if(!isSymmetric(a)||any(!a%in%c(0,1))||any(diag(a)!=0))stop("Malformed simulated network")
    if(any(a[!forward$origin_active,,drop=FALSE]!=0)||any(a[,!forward$origin_active,drop=FALSE]!=0))
      stop("Native structured forecast created or retained ties to an origin-inactive actor")
    b<-as.numeric(sim$sims[[s]][[1]][["milex.beh"]][[1]])
    if(length(b)!=N||any(!is.finite(b))||any(!b%in%1:11))stop("Malformed ordinal behavior forecast")
    if(any(b[!forward$origin_active]!=forward$start_behavior[!forward$origin_active]))
      stop("Native structured forecast changed behavior of an origin-inactive actor")
    sum_network<-sum_network+a;sum_behavior<-sum_behavior+b
  }
  probabilities<-sum_network/S
  dimnames(probabilities)<-list(as.character(packet$nms),as.character(packet$nms))
  prediction<-list(nms=packet$nms,probabilities=probabilities,behavior_mean=sum_behavior/S,
    origin_network=forward$origin_network,origin_behavior=forward$origin_behavior,
    origin_active=forward$origin_active,target=target,simulations=S,seed=seed,
    forecast_schema_version=FORWARD_SCHEMA,
    native_origin_active=as.logical(forward$audit$native_origin_active),
    network_specification_version=NETWORK_SPECIFICATION_VERSION)
  # Same scorer contract, probability-first aggregation and publication order.
  # No target outcomes are read anywhere in this process.
  saveRDS(prediction,file.path(outdir,"predictions.pending.rds"))
  if(!file.rename(file.path(outdir,"predictions.pending.rds"),file.path(outdir,"predictions.rds")))stop("Could not publish predictions")
  ij<-which(upper.tri(probabilities),arr.ind=TRUE)
  write.csv(data.frame(ccode1=packet$nms[ij[,1]],ccode2=packet$nms[ij[,2]],
    probability=probabilities[ij],origin=forward$origin_network[ij]),file.path(outdir,"predictions.csv"),row.names=FALSE)
  write.csv(data.frame(ccode=packet$nms,prediction=sum_behavior/S),file.path(outdir,"behavior_predictions.csv"),row.names=FALSE)
  saveRDS(sim,file.path(outdir,"simulations.rds"))
  audit<-c(forward$audit,list(rates=fwd$rates,centering_corrections=fwd$centering_corrections,
    mean_shift=fwd$mean_shift,seed=seed,requested_simulations=budget,returned_simulations=S,
    elapsed_seconds=unname((proc.time()-started)[3]),target_outcomes_accessed=FALSE,
    network_specification_version=NETWORK_SPECIFICATION_VERSION,
    requested_training_effects=sum(effs$include),fixed_forward_effects=sum(fwd$effects$include)))
  write_json(audit,file.path(outdir,"forecast_audit.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
  write_json(list(status="completed",stage="forecast",next_attempt=NULL,
    timestamp_utc=format(Sys.time(),"%Y-%m-%dT%H:%M:%SZ",tz="UTC"),
    requested_simulations=budget,returned_simulations=S),file.path(outdir,"checkpoint.json"),
    auto_unbox=TRUE,pretty=TRUE,null="null",digits=16)
  invisible(prediction)
}

if(sys.nframe()==0L) {
  args<-commandArgs(trailingOnly=TRUE)
  flag<-function(key,default=NULL){i<-match(key,args);if(is.na(i))default else args[i+1]}
  run_forecast_multiobjective(flag("--spec"),as.integer(flag("--target")),flag("--output"),
    flag("--settings","configs/evaluator-v2.json"),flag("--past"),"--prepare"%in%args)
}
