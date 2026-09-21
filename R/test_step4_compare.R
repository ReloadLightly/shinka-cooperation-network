# Real archived inputs + stopped forecast initializations; zero empirical draws.
source("R/step4_compare.R")
checks<-0L;ok<-function(x,msg){assert(x,msg);checks<<-checks+1L}
refuse<-function(expr)ok(inherits(try(force(expr),silent=TRUE),"try-error"),"Expected rejection")
native_source_check("vendor/RSiena")
requests<-read_json(Sys.getenv("STEP4_REQUESTS"),simplifyVector=FALSE)$requests
settings<-read_json("configs/precision-fit-v1.json",simplifyVector=TRUE)
reports<-list()
for(req in requests){
  model<-req$model;year<-req$target
  packet<-readRDS(file.path(Sys.getenv("STEP4_PAST_DIR"),paste0(year,".rds")))
  train<-make_training_data(packet);spec<-validate_network_specification_v2(req$specification)
  built<-build_network_effects_v2(train,spec);e<-built$effects
  closure<-e[e$include&e$name=="dv.net"&e$shortName%in%c("gwesp","transTriads"),,drop=FALSE]
  ok(nrow(closure)==1L&&closure$shortName==if(model=="reference")"transTriads"else"gwesp","Exactly the declared closure changed")
  ok(closure$parm==if(model=="reference")0 else 69,"Native closure parameter differs")
  baseline<-build_network_effects_v2(train,step4_plan()$models$reference)$effects
  behavior<-function(e)parameter_keys(e[e$include&e$name=="milex.beh",,drop=FALSE])
  ok(identical(behavior(e),behavior(baseline)),"Spending structure changed")
  control<-function(e)parameter_keys(e[e$include&!e$shortName%in%c("gwesp","transTriads"),,drop=FALSE])
  ok(identical(control(e),control(baseline)),"Protected controls changed")
  imports<-req$import_history$attempts;previous<-NULL
  for(a in names(imports)){
    f<-step4_imported_fit(imports[[a]],train,e,spec,settings,as.integer(a),previous)
    ok(length(f$theta)==sum(e$include),"Archived vector dimension differs");previous<-f
  }
  reports[[paste(model,year,sep="/")]]<-list(parameters=sum(e$include),archived_checkpoints_verified=length(imports),closure=closure$shortName,parameter=closure$parm)
}
# Both historical-valid short and rescued-long records must reach the new
# forecast route with actual_n3. Fixtures are NOT published as policy acceptances.
for(case in c("short","rescued")){
  year<-if(case=="short")2008L else 2009L
  packet<-readRDS(file.path(Sys.getenv("STEP4_PAST_DIR"),paste0(year,".rds")));train<-make_training_data(packet)
  spec<-validate_network_specification_v2(step4_plan()$models$reference)
  e<-build_network_effects_v2(train,spec)$effects
  f<-if(case=="short")readRDS(file.path(step4_plan()$baseline_cache_folders[[as.character(year)]],"accepted_fit.rds"))$fit else readRDS("results/diagnostics/convergence-pilot-v1/diagnostic.rds")
  f<-v2_adopt_legacy_fit(f,e,spec);n3<-if(case=="short")1000L else 3000L
  d<-fit_diagnostics(f,n3);ok(d$valid,"Saved fixture is not acceptable")
  cell<-tempfile("step4-receipt-test-");dir.create(cell);dir.create(file.path(cell,"fit"))
  ans<-list(fit=f,diagnostics=list(list(attempt=3L)),accepted_attempt=3L,
    convergence_policy=PRECISION_VERSION,authoritative_n3=n3,authoritative_diagnostics=d)
  saveRDS(ans,file.path(cell,"fit","accepted_fit.rds"));precision_json(spec,file.path(cell,"specification.json"))
  verified<-step4_receipt(file.path(cell,"fit","accepted_fit.rds"),e);ok(verified$authoritative_n3==n3,"Receipt budget not honored")
  res<-step4_forward(cell,file.path(Sys.getenv("STEP4_PAST_DIR"),paste0(year,".rds")),"reference",year,1L,verify_only=TRUE)
  ok(res$status=="verified_without_simulation"&&res$authoritative_n3==n3,"New receipt forecast path did not initialize")
  ans$authoritative_n3<-if(n3==1000L)3000L else 1000L
  saveRDS(ans,file.path(cell,"fit","accepted_fit.rds"));refuse(step4_receipt(file.path(cell,"fit","accepted_fit.rds")))
  unlink(cell,recursive=TRUE)
}
# Native GWESP weights from the pinned implementation (parameter/100).
alpha<-.69;q<-1-exp(-alpha);w<-function(m)exp(alpha)*(1-q^m)
ok(abs(w(1)-1)<1e-14&&w(20)<exp(alpha)&&w(20)>w(3),"GWESP saturation property")
ok(w(3)-w(2)<w(2)-w(1),"Diminishing shared-partner increment")
report<-list(status="passed",checks=checks,models=reports,real_receipt_forecast_initializations_stopped=2L,
  new_empirical_simulations=0L,new_fits=0L,target_packets_read=0L,
  statement="Verified importer identities and actual_n3 forecast consumption. Full new policy fits/forecasts remain part of the declared Step 4 execution.")
write_json(report,Sys.getenv("STEP4_PREFLIGHT_REPORT"),auto_unbox=TRUE,pretty=TRUE,digits=17)
cat(toJSON(report,auto_unbox=TRUE,pretty=TRUE),"\n")
