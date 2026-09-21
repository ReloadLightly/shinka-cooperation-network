# Native-runtime integration tests. All numerical results are saved fixtures.
# No siena07 estimation, simulation, forecasting or outcome scoring is permitted.
source("R/precision_convergence.R")
checks<-0L
ok<-function(x,msg){assert(x,msg);checks<<-checks+1L}
refuse<-function(expr){ok(inherits(try(force(expr),silent=TRUE),"try-error"),"Expected refusal")}
settings<-read_json("configs/precision-fit-v1.json",simplifyVector=TRUE)
precision_policy(settings)
config<-read_json("configs/convergence-preflight-v1.json",simplifyVector=TRUE)
third<-readRDS(config$fit_path)
fourth<-readRDS(file.path(dirname(config$fit_path),"accepted_fit.rds"))$fit
pilot<-readRDS("results/diagnostics/convergence-pilot-v1/diagnostic.rds")
d<-fit_diagnostics(third,1000L)
ok(precision_action(d,1000L)=="assess_once","Failed short reference needs precision")
pass<-d;pass$overall_maximum_convergence<-0.2;pass$valid<-TRUE
ok(precision_action(pass,1000L)=="accept_original","Preserve valid short acceptance")
long<-fit_diagnostics(pilot,3000L)
ok(precision_action(long,3000L)=="accept_original","Valid long assessment accepted")
failedlong<-long;failedlong$overall_maximum_convergence<-0.3;failedlong$valid<-FALSE
ok(precision_action(failedlong,3000L)=="continue_original","Failed long fit has no extra chance")
for(n in c("native_ok","phase3_complete","finite_identified","covariance_all_finite")){
  bad<-d;bad[[n]]<-FALSE;ok(precision_action(bad,1000L)=="continue_original",paste("Non-ratio failure",n))
}
for(n in c("divergence","fixed_parameters","newly_fixed_parameters")){
  bad<-d;bad[[n]]$any<-TRUE;ok(precision_action(bad,1000L)=="continue_original",paste("Flags",n))
}
bad<-d;bad$covariance_message<-"warning";ok(precision_action(bad,1000L)=="continue_original","Covariance warning not rescued")
for(pair in list(c(0.1,0.2),c(0.05,0.25))){
  edge<-d;edge$maximum_absolute_t_ratio<-pair[1];edge$overall_maximum_convergence<-pair[2]
  ok(precision_action(edge,1000L)=="assess_once","Strict threshold equality must fail")
}
refuse(precision_action(d,2000L))
refuse(precision_seed(2010,1L))
ok(identical(precision_seed(2009L,3L),52020093L),"Fixed seed mapping")
ok(length(unique(unlist(lapply(2006:2009,function(y)vapply(1:4,function(a)precision_seed(y,a),integer(1))))))==16L,"No seed collision")
x<-precision_algorithm(third,tempfile(),precision_seed(2009,1))
ok(x$nsub==0L&&x$n3==3000L&&!x$simOnly&&!x$useStdInits,"Phase-3 route")
for(n in setdiff(names(third$x),c("nsub","n3","randomSeed","projname","FRAN")))
  assert(identical(x[[n]],third$x[[n]]),paste("Changed inherited algorithm setting",n))
checks<-checks+1L

# Replay source data, not an estimate under the NEW seed. Outcomes are fixtures.
newdir<-function(){p<-tempfile();dir.create(p);writeLines('{}',file.path(p,"request.json"));p}
optcalls<-0L;assesscalls<-0L
optimizer<-function(netdata,effs,settings,outdir,attempt,previous){optcalls<<-optcalls+1L;third}
assessor<-function(fit,netdata,effs,seed,folder){assesscalls<<-assesscalls+1L;pilot}
out<-newdir()
ans<-fit_model_precision(NULL,NULL,settings,out,2009,optimizer,assessor)
ok(ans$authoritative_n3==3000L&&ans$accepted_attempt==1L,"Precision result consumed by estimator")
ok(optcalls==1L&&assesscalls==1L,"Exactly one mock callback per phase")
again<-fit_model_precision(NULL,NULL,settings,out,2009,optimizer,assessor)
ok(optcalls==1L&&assesscalls==1L&&identical(ans$fit$theta,again$fit$theta),"Resume cached acceptance with zero callbacks")
unlink(out,recursive=TRUE)

# A failed check must continue from ORIGINAL fit, not the diagnostic object's matrices.
optcalls<-0L;assesscalls<-0L;received_original<-FALSE
optimizer<-function(netdata,effs,settings,outdir,attempt,previous){
  optcalls<<-optcalls+1L
  if(attempt==1L)return(third)
  received_original<<-identical(previous,third)
  done<-third;done$tconv.max<-0.2;done
}
assessor<-function(fit,netdata,effs,seed,folder){assesscalls<<-assesscalls+1L;bad<-pilot;bad$tconv.max<-0.3;bad}
out<-newdir();ans<-fit_model_precision(NULL,NULL,settings,out,2009,optimizer,assessor)
ok(optcalls==2L&&assesscalls==1L&&received_original,"Continuation uses original checkpoint")
ok(ans$authoritative_n3==1000L&&ans$accepted_attempt==2L,"Short success retains its budget")
unlink(out,recursive=TRUE)

# The identical vector cannot obtain a new precision seed on a subsequent request.
out<-newdir();assesscalls<-0L
one<-precision_assess_once(third,NULL,NULL,2009,1L,out,assessor)
two<-precision_assess_once(third,NULL,NULL,2009,2L,out,assessor)
ok(assesscalls==1L&&two$reused&&two$metadata$seed==precision_seed(2009,1L),"No unchanged-vector seed shopping")
folder<-file.path(out,"precision",precision_vector_key(third));writeLines("tampered",file.path(folder,"result.rds"))
refuse(precision_assess_once(third,NULL,NULL,2009,1L,out,assessor));unlink(out,recursive=TRUE)
out<-newdir();folder<-file.path(out,"precision",precision_vector_key(third));dir.create(folder,recursive=TRUE)
refuse(precision_assess_once(third,NULL,NULL,2009,1L,out,assessor));unlink(out,recursive=TRUE)

# Nine genuinely NEW saved observations and prior pilot are replay data.
for(label in c("attempt3","attempt4"))for(seed in if(label=="attempt3")2009302:2009305 else 2009401:2009405){
  summary<-read_json(file.path("results/diagnostics/convergence-repeatability-v1",label,seed,"summary.json"),simplifyVector=TRUE)
  d<-summary$native_diagnostics
  ok(precision_action(d,3000L)=="accept_original",paste("Saved full diagnostic",label,seed))
  short<-d;short$valid<-FALSE;short$phase3_iterations<-1000L
  short$maximum_absolute_t_ratio<-summary$fresh_first_1000$maximum_absolute_t
  short$overall_maximum_convergence<-summary$fresh_first_1000$overall
  ok(precision_action(short,1000L)=="assess_once",paste("Saved prefix routes to assessment",label,seed))
}

# REAL initialization at the new seed, stopping before any simulator.
packet<-readRDS(Sys.getenv("PRECISION_TEST_PAST"))
net<-make_training_data(packet)
spec<-list(schema_version=2L,network_effects=list(list(effect="degPlus",parameter=1L),list(effect="transTriads",parameter=0L)))
built<-build_network_effects_v2(net,spec)
init<-list()
for(label in c("attempt3","attempt4")){
  fit<-v2_adopt_legacy_fit(if(label=="attempt3")third else fourth,built$effects,spec)
  folder<-tempfile();dir.create(folder)
  result<-precision_native_assessment(fit,net,built$effects,precision_seed(2009,1L),folder,verify_only=TRUE)
  ok(result$status=="initialization_verified_no_simulation"&&result$new_simulations==0L,"Real source-vector initialization")
  init[[label]]<-result;unlink(folder,recursive=TRUE)
}
report<-list(status="passed",version=PRECISION_VERSION,checks=checks,new_simulations=0L,
  new_refits=0L,new_forecasts=0L,target_packets_read=0L,
  saved_diagnostic_replay=TRUE,replay_is_not_a_new_seed_result=TRUE,
  real_stopped_initializations=init,live_production_assessment_not_executed=TRUE)
write_json(report,Sys.getenv("PRECISION_TEST_REPORT"),pretty=TRUE,auto_unbox=TRUE,digits=17)
cat(toJSON(report,auto_unbox=TRUE,pretty=TRUE),"\n")
