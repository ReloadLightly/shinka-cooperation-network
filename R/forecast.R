#!/usr/bin/env Rscript
# Predictor process. Does not open targets or raw archive.
source("R/empirical.R")
FORWARD_SCHEMA <- "training-only-v2-fixed-origin-membership"

carry_last <- function(x, fallback) {
  apply(x,1,function(z) { good<-which(is.finite(z)); if(length(good)) z[max(good)] else fallback })
}
cpp_behavior_mean <- function(x) mean(colMeans(x,na.rm=TRUE))

make_forward_data <- function(packet,train) {
  d <- packet$data; T <- length(packet$years); N <- length(packet$nms)
  origin_network <- d[[NET_DV]][,,T]
  origin_behavior <- d[[BEH_DV]][,T]
  active <- packet$present[,T]
  start <- origin_network
  miss <- which(!is.finite(start),arr.ind=TRUE)
  if(nrow(miss)) for(k in seq_len(nrow(miss))) {
    ij<-miss[k,]; z<-d[[NET_DV]][ij[1],ij[2],];good<-which(is.finite(z)); start[ij[1],ij[2]] <- if(length(good)) z[max(good)] else 0
  }
  # Countries absent at the origin are represented but cannot retain active ties.
  start[!active,]<-0;start[,!active]<-0
  diag(start)<-0
  if(!isSymmetric(start)||any(!start%in%c(0,1))) stop("Invalid origin network after declared training-only imputation")
  modeb <- as.numeric(names(which.max(table(d[[BEH_DV]]))))
  start_b <- carry_last(d[[BEH_DV]],modeb)
  # Native C++ determines support from both supplied waves. A duplicate origin
  # can inadvertently shrink historical support. Put the historical min/max in
  # two placeholder entries, and compensate its known mean algebraically below.
  # This is not observed future data and does not impose endpoint constraints:
  # allowOnly=FALSE + cond=FALSE + simOnly=TRUE + all coefficients fixed.
  placeholder_b <- start_b
  support <- range(train$depvars$milex.beh,na.rm=TRUE)
  placeholder_b[1:2] <- support
  # RSiena 1.3.10's ordinary proposal code comments out its receiver-activity
  # check. Native structural-zero code 10 is therefore necessary to prevent
  # active actors creating ties to actors known absent at the origin.
  # Only those ineligible dyads are constrained; eligible ties remain free.
  scaffold_network <- start
  inactive_pairs <- outer(!active,rep(TRUE,N),"&") | outer(rep(TRUE,N),!active,"&")
  diag(inactive_pairs)<-FALSE
  scaffold_network[inactive_pairs]<-10
  stopifnot(all(scaffold_network[inactive_pairs]==10),
            !any(scaffold_network[!inactive_pairs] %in% c(10,11)))
  args <- list(dv.net=sienaDependent(array(c(scaffold_network,scaffold_network),c(N,N,2)),type="oneMode",allowOnly=FALSE),
               milex.beh=sienaDependent(cbind(start_b,placeholder_b),type="behavior",allowOnly=FALSE))
  for(v in MONADIC) {
    old <- train$vCovars[[paste0("beh.",v)]]
    mu <- attr(old,"mean")
    x <- carry_last(d[[paste0("m.",v)]],mu)
    # Values stored by coCovar with centered=FALSE are used directly by C++.
    args[[paste0("beh.",v)]] <- coCovar(x-mu,centered=FALSE)
  }
  for(v in DYADIC) {
    old <- if(v=="lndistance_d") train$dycCovars[[paste0("nets.",v)]] else train$dyvCovars[[paste0("nets.",v)]]
    mu <- attr(old,"mean")
    a <- d[[paste0("d.",v)]]; x <- a[,,T]
    missing <- which(!is.finite(x),arr.ind=TRUE)
    if(nrow(missing)) for(k in seq_len(nrow(missing))) {
      ij<-missing[k,];z<-a[ij[1],ij[2],];good<-which(is.finite(z));x[ij[1],ij[2]]<-if(length(good)) z[max(good)] else mu
    }
    x <- x-mu;diag(x)<-0
    args[[paste0("nets.",v)]] <- coDyadCovar(x,centered=FALSE)
  }
  # Hold origin membership fixed; no realized target entry/exit information.
  # IMPORTANT: native unpackCompositionChange DROPS time-zero events. Encoding
  # an absent actor as c(1,1) incorrectly leaves it active in the first period.
  # Build the standard container, then set its native activity/action matrices
  # directly to the known origin membership for BOTH scaffold waves. This
  # pinned-version adapter changes data bookkeeping, never the native engine.
  args$cc <- sienaCompositionChange(rep(list(c(1,2)),N))
  net <- do.call(sienaDataCreate,args)
  cc <- net$compositionChange[[1]]
  activity <- matrix(rep(active,2),nrow=N,ncol=2)
  actions <- matrix(0L,nrow=N,ncol=2);actions[!active,]<-1L
  attr(cc,"activeStart")<-activity
  attr(cc,"action")<-actions
  attr(cc,"events")<-attr(cc,"events")[FALSE,,drop=FALSE]
  net$compositionChange[[1]]<-cc
  native_composition <- RSiena:::unpackCompositionChange(cc)
  stopifnot(identical(native_composition$activeStart,activity),
            nrow(native_composition$events)==0L,
            !any(native_composition$activeStart[!active,,drop=FALSE]))
  stopifnot(!any(attr(net$depvars$dv.net,"uponly")),!any(attr(net$depvars$dv.net,"downonly")),
            !any(attr(net$depvars$milex.beh,"uponly")),!any(attr(net$depvars$milex.beh,"downonly")))
  if(!identical(as.numeric(range(net$depvars$milex.beh,na.rm=TRUE)),as.numeric(support))) stop("Native forward behavior support differs from training")
  list(netdata=net,origin_network=origin_network,origin_behavior=origin_behavior,
       origin_active=active,start_network=start,start_behavior=start_b,
       audit=list(forecast_schema_version=FORWARD_SCHEMA,
                  native_origin_active=as.logical(native_composition$activeStart[,1]),
                  native_composition_events=nrow(native_composition$events),
                  origin_membership_native_verified=TRUE,
                  inactive_dyads_native_structural_zero=sum(upper.tri(start)&inactive_pairs),
                  active_dyads_have_no_structural_constraints=TRUE,
                  network_missing_at_origin=nrow(miss),behavior_missing_at_origin=sum(!is.finite(origin_behavior)),
                  inactive_at_origin=packet$nms[!active],support=support,
                  placeholder="duplicate origin network; origin behavior with two historical boundary values",
                  conditional=FALSE,simOnly=TRUE,allowOnly=FALSE,
                  training_behavior_mean=cpp_behavior_mean(train$depvars$milex.beh[,1,]),
                  forward_behavior_mean=cpp_behavior_mean(net$depvars$milex.beh[,1,]),
                  covariate_centering="training means preserved; missing origin values last known then training mean"))
}

forward_effects <- function(forward,train,fit,terms) {
  eff <- model_effects(forward$netdata,terms)
  fitted <- fit$requestedEffects
  if(nrow(fitted)!=length(fit$theta)) stop("Native fitted-effect mapping has unexpected shape")
  fitted$estimate <- fit$theta
  idx <- which(eff$include)
  rates <- list()
  for(i in idx) {
    if(eff$type[i]=="rate") {
      rows <- which(fitted$name==eff$name[i] & fitted$type=="rate" & fitted$shortName==eff$shortName[i])
      rows <- rows[is.finite(fitted$estimate[rows])]
      if(!length(rows))stop("No estimable training rate for ",eff$name[i])
      row <- rows[which.max(as.numeric(fitted$period[rows]))]
      value<-fitted$estimate[row]
      if(value<=0)stop("Nonpositive carried rate")
      eff$initialValue[i]<-value
      rates[[eff$name[i]]]<-list(value=value,training_period=fitted$period[row],duration_adjustment=1)
    } else {
      rows<-which(effect_key(fitted)==effect_key(eff)[i])
      if(length(rows)!=1)stop("Ambiguous fitted effect mapping: ",effect_key(eff)[i])
      eff$initialValue[i]<-fitted$estimate[rows]
    }
  }
  # In native C++, altX(milex.beh) uses z_j-mu, and quadratic behavior
  # uses (z_i-mu)^2. Recenter exactly, preserving each change statistic:
  # beta_density' = beta_density + beta_alt*(mu_forward-mu_train)
  # beta_linear' = beta_linear + 2*beta_quadratic*(mu_forward-mu_train).
  shift<-forward$audit$forward_behavior_mean-forward$audit$training_behavior_mean
  one<-function(name,short,interaction="") {
    k<-which(eff$include & eff$name==name & eff$shortName==short & eff$interaction1==interaction)
    if(length(k)!=1)stop("Missing centering correction effect ",name,"/",short);k
  }
  density<-one("dv.net","density")
  alt<-one("dv.net","altX","milex.beh")
  linear<-one("milex.beh","linear")
  quadratic<-one("milex.beh","quad")
  corrections<-c(density=eff$initialValue[alt]*shift,linear=2*eff$initialValue[quadratic]*shift)
  eff$initialValue[density]<-eff$initialValue[density]+corrections["density"]
  eff$initialValue[linear]<-eff$initialValue[linear]+corrections["linear"]
  eff$fix[eff$include]<-TRUE
  list(effects=eff,rates=rates,centering_corrections=as.list(corrections),mean_shift=shift)
}

run_forecast <- function(specfile,target,outdir,settingsfile,pastfile=NULL,prepare_only=FALSE) {
  dir.create(outdir,recursive=TRUE,showWarnings=FALSE)
  spec<-read_json(specfile,simplifyVector=TRUE);terms<-validate_spec(spec)
  settings<-read_json(settingsfile,simplifyVector=TRUE)
  stopifnot(as.character(packageVersion("RSiena"))==settings$software$RSiena)
  packet<-readRDS(pastfile %||% file.path("data/past",paste0(target,".rds")))
  stopifnot(identical(as.integer(packet$years),1990:(as.integer(target)-1L)))
  train<-make_training_data(packet);effs<-model_effects(train,terms)
  write.csv(effect_table(effs[effs$include,]),file.path(outdir,"training_effects.csv"),row.names=FALSE)
  forward<-make_forward_data(packet,train)
  write_json(forward$audit,file.path(outdir,"preflight_audit.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
  if(prepare_only) {saveRDS(list(train=train,effects=effs,forward=forward),file.path(outdir,"prepared.rds"));return(invisible(TRUE))}
  fit_path<-file.path(outdir,"accepted_fit.rds")
  if(file.exists(fit_path)) {
    ans<-readRDS(fit_path)
    accepted_attempt <- tail(ans$diagnostics,1)[[1]]$attempt
    if(!fit_diagnostics(ans$fit,fit_schedule(settings,accepted_attempt)$n3)$valid)stop("Cached fit is not acceptable")
  } else {
    ans<-fit_model(train,effs,settings,outdir);saveRDS(ans,fit_path)
  }
  fwd<-forward_effects(forward,train,ans$fit,terms)
  seed<-as.integer(target)*1000L+1L
  if(!is.null(settings$forecast$seed_override))seed<-settings$forecast$seed_override
  budget<-as.integer(settings$forecast$simulations)
  alg<-sienaAlgorithmCreate(projname=file.path(outdir,"forecast"),cond=FALSE,useStdInits=FALSE,nsub=0,n3=budget,
    seed=seed,modelType=c(dv.net=3),behModelType=c(milex.beh=1),simOnly=TRUE)
  started<-proc.time()
  sim<-siena07(alg,data=forward$netdata,effects=fwd$effects,batch=TRUE,silent=TRUE,useCluster=FALSE,returnDeps=TRUE)
  S<-length(sim$sims)
  if(S!=budget)stop("Returned endpoint count ",S," differs from fixed budget ",budget)
  N<-length(packet$nms);sum_network<-matrix(0,N,N);sum_behavior<-numeric(N)
  for(s in seq_len(S)) {
    edges<-sim$sims[[s]][[1]][["dv.net"]][[1]]
    a<-matrix(0,N,N)
    if(length(edges))a[edges[,1:2,drop=FALSE]]<-edges[,3]
    if(!isSymmetric(a)||any(!a%in%c(0,1)))stop("Malformed simulated network")
    if(any(a[!forward$origin_active,,drop=FALSE]!=0)||any(a[,!forward$origin_active,drop=FALSE]!=0))
      stop("Native forecast created or retained ties to an origin-inactive actor")
    b<-as.numeric(sim$sims[[s]][[1]][["milex.beh"]][[1]])
    if(length(b)!=N||any(!is.finite(b)))stop("Malformed behavior forecast")
    if(any(b[!forward$origin_active]!=forward$start_behavior[!forward$origin_active]))
      stop("Native forecast changed behavior of an origin-inactive actor")
    sum_network<-sum_network+a;sum_behavior<-sum_behavior+b
  }
  probabilities<-sum_network/S;dimnames(probabilities)<-list(as.character(packet$nms),as.character(packet$nms))
  prediction<-list(nms=packet$nms,probabilities=probabilities,behavior_mean=sum_behavior/S,
    origin_network=forward$origin_network,origin_behavior=forward$origin_behavior,origin_active=forward$origin_active,
    target=target,simulations=S,seed=seed,forecast_schema_version=FORWARD_SCHEMA,
    native_origin_active=as.logical(forward$audit$native_origin_active))
  # Publish predictions atomically BEFORE the separate scorer opens targets.
  saveRDS(prediction,file.path(outdir,"predictions.pending.rds"));file.rename(file.path(outdir,"predictions.pending.rds"),file.path(outdir,"predictions.rds"))
  ij<-which(upper.tri(probabilities),arr.ind=TRUE)
  write.csv(data.frame(ccode1=packet$nms[ij[,1]],ccode2=packet$nms[ij[,2]],probability=probabilities[ij],origin=forward$origin_network[ij]),file.path(outdir,"predictions.csv"),row.names=FALSE)
  write.csv(data.frame(ccode=packet$nms,prediction=sum_behavior/S),file.path(outdir,"behavior_predictions.csv"),row.names=FALSE)
  saveRDS(sim,file.path(outdir,"simulations.rds"))
  audit<-c(forward$audit,list(rates=fwd$rates,centering_corrections=fwd$centering_corrections,mean_shift=fwd$mean_shift,
    seed=seed,requested_simulations=budget,returned_simulations=S,elapsed_seconds=unname((proc.time()-started)[3]),
    target_outcomes_accessed=FALSE))
  write_json(audit,file.path(outdir,"forecast_audit.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
  write.csv(effect_table(fwd$effects[fwd$effects$include,]),file.path(outdir,"forecast_effects.csv"),row.names=FALSE)
  invisible(prediction)
}
if(sys.nframe()==0L) {
  args<-commandArgs(trailingOnly=TRUE)
  flag<-function(key,default=NULL){i<-match(key,args);if(is.na(i))default else args[i+1]}
  run_forecast(flag("--spec"),as.integer(flag("--target")),flag("--output"),flag("--settings","configs/evaluator-v1.json"),flag("--past"),"--prepare"%in%args)
}
