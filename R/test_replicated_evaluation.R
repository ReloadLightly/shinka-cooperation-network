# Deterministic and native read-only checks. No production simulations or fits.
source("R/replicated_evaluation.R")
count<-0L
check<-function(x,msg){assert(isTRUE(x),msg);count<<-count+1L}
evidence<-Sys.getenv("SHINKA_REPLICATED_EVIDENCE_ROOT")
pastdir<-Sys.getenv("STEP5A_PAST_DIR")
out<-Sys.getenv("STEP5A_NATIVE_REPORT")
check(nzchar(evidence)&&nzchar(pastdir)&&nzchar(out),"Explicit test paths required")
check(as.character(getRversion())=="4.2.1"&&as.character(packageVersion("RSiena"))=="1.3.10","Pinned native runtime")
# This arithmetic fixture contains no model observations.
fixture<-lapply(list(c(.997,.998),c(.999,.999),c(.998,.997),c(.999,.998),c(.997,.998)),
                function(x)list(probabilities=matrix(x,1,2),simulations=1000L))
p<-network_count_pool(fixture,1:5)
check(identical(p,network_count_pool(fixture,c(5,2,4,3,1))),"Integer pool is permutation invariant")
check(all(p*5000==round(p*5000)),"Integer pool preserves grid")
check(p[1]==p[2],"Equal successes stay tied")
# Preserve exact decision fields; tolerate only report-only spectral roundoff.
fixture_actual<-list(valid=TRUE,maximum_absolute_t_ratio=0.05,overall_maximum_convergence=0.2,
  estimates=c(1,2),covariance_minimum_eigenvalue=0.000005,covariance_condition_number=1700000)
fixture_report<-fixture_actual;fixture_report$covariance_minimum_eigenvalue<-0.000005*(1+1e-11)
check(replicated_diagnostics_match(fixture_actual,fixture_report),"Spectral reporting roundoff is portable")
fixture_bad<-fixture_report;fixture_bad$overall_maximum_convergence<-fixture_bad$overall_maximum_convergence+1e-15
check(!replicated_diagnostics_match(fixture_actual,fixture_bad),"Acceptance ratio comparisons remain exact")
fixture_bad<-fixture_report;fixture_bad$estimates[1]<-fixture_bad$estimates[1]+1e-12
check(!replicated_diagnostics_match(fixture_actual,fixture_bad),"Coefficient comparisons remain exact")
fixture_bad<-fixture_report;fixture_bad$valid<-FALSE
check(!replicated_diagnostics_match(fixture_actual,fixture_bad),"Invalid recorded evidence cannot pass")
fixture_bad<-fixture_report;fixture_bad$covariance_condition_number<-1701000
check(!replicated_diagnostics_match(fixture_actual,fixture_bad),"Large spectral reporting differences refused")
verified<-list();initializations<-0L
for(model in c("reference","gwesp69"))for(year in 2006:2009){
  cell<-file.path(evidence,"results/step4-closure-comparison-v1",model,year)
  a<-step4_receipt(file.path(cell,"fit/accepted_fit.rds"))
  record<-read_json(file.path(cell,"fit/accepted.json"),simplifyVector=FALSE)
  check(isTRUE(a$authoritative_diagnostics$valid),"Saved native receipt valid")
  check(record$authoritative_n3==a$authoritative_n3,"Authoritative n3 agrees")
  packet<-readRDS(file.path(pastdir,paste0(year,".rds")))
  train<-make_training_data(packet)
  spec<-validate_network_specification_v2(read_json(file.path(cell,"specification.json"),simplifyVector=FALSE))
  built<-build_network_effects_v2(train,spec)
  updated<-v2_update_theta(built$effects,a$fit)
  check(identical(as.numeric(updated$initialValue[updated$include]),as.numeric(a$fit$theta)),"Native fitted vector maps exactly")
  check(length(a$fit$theta)==52L+2L*(year-2006L),"Expected historical parameter dimension")
  if((model=="reference"&&year==2006L)||(model=="gwesp69"&&year==2007L)){
    tmp<-tempfile("replicated-stopped-");dir.create(tmp);dir.create(file.path(tmp,"fit"))
    file.copy(file.path(cell,"fit/accepted_fit.rds"),file.path(tmp,"fit/accepted_fit.rds"))
    file.copy(file.path(cell,"specification.json"),file.path(tmp,"specification.json"))
    req<-read_json(file.path(cell,"request.json"),simplifyVector=FALSE)
    req$version<-REPLICATED_VERSION;req$model<-paste0("canonical-fixture-",model)
    precision_json(req,file.path(tmp,"request.json"))
    step4_seed<-replicated_bind(tmp)
    before<-precision_sha(file.path(tmp,"fit/accepted_fit.rds"))
    v<-step4_forward(tmp,file.path(pastdir,paste0(year,".rds")),req$model,year,1L,verify_only=TRUE)
    check(identical(v$status,"verified_without_simulation"),"New generalized seed/receipt route stopped before simulation")
    check(identical(before,precision_sha(file.path(tmp,"fit/accepted_fit.rds"))),"Stopped initialization did not alter saved fit")
    initializations<-initializations+1L;unlink(tmp,recursive=TRUE)
  }
  verified[[paste(model,year,sep="/")]]<-list(parameters=length(a$fit$theta),authoritative_n3=a$authoritative_n3)
}
# Build an admissible third specification; do not pretend it has estimated coefficients.
spec<-list(schema_version=2L,network_effects=list(list(effect="degPlus",parameter=2L),list(effect="gwesp",parameter=40L),list(effect="outInv",parameter=1L)))
packet<-readRDS(file.path(pastdir,"2006.rds"));built<-build_network_effects_v2(make_training_data(packet),validate_network_specification_v2(spec))
check(sum(built$effects$include)==53L,"Generic non-Step4 three-term specification reaches native builder")
precision_json(list(status="passed",checks=count,verified_receipts=verified,
  stopped_forecast_initializations=initializations,novel_specification_built_not_estimated=TRUE,
  new_fits=0L,new_forecasts=0L,new_simulations=0L,target_packets_read=0L),out)
