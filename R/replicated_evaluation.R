# Generalized replicated consumer. The original Step 4 and paper adapters remain
# unchanged. Rebind only the two-model seed lookup and version in this process;
# native fit, receipt validation, centering, forecast, pooling and scoring reuse
# the measured implementation. Never import a reference coefficient into another model.
source("R/step4_compare.R")
source("R/replicated_score_view.R")
REPLICATED_VERSION <- "multiobjective-replicated-v1"
STEP4_VERSION <- REPLICATED_VERSION
# Native spectral summaries are report-only and can differ at roundoff on a
# different BLAS/CPU. All acceptance fields and coefficient-derived values must
# remain EXACT; only these two recomputed reporting fields admit a 1e-8 relative
# comparison. This never changes the strict convergence or native-validity gate.
replicated_diagnostics_match <- function(actual,recorded) {
  reporting<-c("covariance_minimum_eigenvalue","covariance_condition_number")
  if(!identical(names(actual),names(recorded))||!isTRUE(actual$valid)||!isTRUE(recorded$valid))return(FALSE)
  exact<-setdiff(names(actual),reporting)
  if(!identical(actual[exact],recorded[exact]))return(FALSE)
  all(vapply(reporting,function(k){
    a<-actual[[k]];b<-recorded[[k]]
    length(a)==1L&&length(b)==1L&&is.finite(a)&&is.finite(b)&&
      abs(a-b)<=1e-8*max(abs(a),abs(b),.Machine$double.xmin)
  },logical(1)))
}
replicated_receipt <- function(path,effects=NULL) {
  ans<-readRDS(path)
  assert(identical(ans$convergence_policy,PRECISION_VERSION)&&ans$accepted_attempt%in%1:4&&
    ans$authoritative_n3%in%c(1000L,3000L),"Missing explicit precision acceptance")
  actual<-fit_diagnostics(ans$fit,ans$authoritative_n3)
  assert(replicated_diagnostics_match(actual,ans$authoritative_diagnostics),
    "Receipt acceptance fields or spectral reporting evidence disagree")
  assert(tail(ans$diagnostics,1)[[1]]$attempt==ans$accepted_attempt,"Receipt history ends at wrong attempt")
  if(!is.null(effects))v2_update_theta(effects,ans$fit)
  # Return the immutable recorded receipt, not a rewritten diagnosis.
  ans
}
# Private process binding used by the inherited fit and forecast consumers.
step4_receipt<-replicated_receipt
replicated_request <- function(cell) {
  req <- read_json(file.path(cell,"request.json"),simplifyVector=FALSE)
  assert(identical(req$version,REPLICATED_VERSION),"Wrong replicated request")
  assert(req$target %in% 2006:2009,"Development targets only")
  validate_network_specification_v2(req$specification)
  assert(length(req$forecast_seeds)==5L,"Five declared forecast seeds required")
  assert(length(unique(unlist(req$forecast_seeds)))==5L,"Duplicate forecast seeds")
  for(s in req$forecast_seeds)assert(is.finite(s)&&s==as.integer(s)&&s>0,"Invalid R seed")
  req
}
replicated_bind <- function(cell) {
  req<-replicated_request(cell)
  function(year,model,batch) {
    assert(year==req$target&&identical(model,req$model)&&batch%in%1:5,"Request/forward scope differs")
    as.integer(req$forecast_seeds[[batch]])
  }
}
replicated_pool <- function(cell) {
  # Preserve existing spending pooling; correct only network-count ties.
  pp<-lapply(1:5,function(b)readRDS(file.path(cell,"forecasts",b,"predictions.rds")))
  fields<-setdiff(names(pp[[1]]),c("probabilities","behavior_mean","seed","simulations"))
  for(p in pp)for(k in fields)assert(identical(p[[k]],pp[[1]][[k]]),"Pool scope mismatch")
  combine<-function(ix){p<-pp[[1]];p$probabilities<-network_count_pool(pp,ix)
    p$behavior_mean<-Reduce(`+`,lapply(pp[ix],`[[`,"behavior_mean"))/length(ix)
    p$simulations<-1000L*length(ix);p$seed<-NULL;p$batch_seeds<-vapply(pp[ix],`[[`,integer(1),"seed");p}
  out<-file.path(cell,"pooled");dir.create(out,showWarnings=FALSE)
  precision_save(combine(1:5),file.path(out,"predictions.rds"))
  for(b in 1:5)precision_save(combine(setdiff(1:5,b)),file.path(out,paste0("delete-",b,".rds")))
  invisible(NULL)
}
replicated_failure <- function(cell,message) {
  rows<-list();fitdir<-file.path(cell,"fit")
  if(dir.exists(fitdir))for(path in list.files(fitdir,pattern="fit.rds$",recursive=TRUE,full.names=TRUE)) {
    value<-tryCatch(readRDS(path),error=function(e)NULL)
    if(!is.null(value)&&inherits(value,"sienaFit")) {
      d<-tryCatch(fit_diagnostics(value,as.integer(value$x$n3)),error=function(e)list(error=conditionMessage(e)))
      rows[[length(rows)+1L]]<-list(file=path,diagnostics=d)
    }
  }
  checkpoint<-file.path(fitdir,"checkpoint.json")
  cp<-if(file.exists(checkpoint))read_json(checkpoint,simplifyVector=FALSE) else list()
  kind<-if(identical(cp$status,"paused_execution_window"))"boundary_paused" else
    if(grepl("Precision policy exhausted",message,fixed=TRUE))"numerical_policy_exhausted" else "native_execution_error"
  path<-file.path(cell,"last-native-error.json")
  jsonlite::write_json(list(kind=kind,message=message,completed_fit_diagnostics=rows,fitness=NULL),path,auto_unbox=TRUE,pretty=TRUE,digits=17,na="null",null="null")
  kind
}
if(sys.nframe()==0L) {
  args<-commandArgs(trailingOnly=TRUE)
  assert(length(args)>=2L,"Explicit operation and cell required")
  assert(as.character(getRversion())=="4.2.1"&&as.character(packageVersion("RSiena"))=="1.3.10","Wrong pinned runtime")
  cell<-args[2];req<-replicated_request(cell)
  step4_seed<-replicated_bind(cell)
  status<-tryCatch({
    mode<-args[1]
    if(mode=="fit")step4_fit(cell,args[3],args[4],as.integer(args[5]))
    else if(mode=="forecast")step4_forward(cell,args[3],args[4],as.integer(args[5]),as.integer(args[6]))
    else if(mode=="pool")replicated_pool(cell)
    else if(mode=="score")step4_score(cell,args[3])
    else stop("Unknown explicit replicated operation")
    0L
  },error=function(e){
    kind<-replicated_failure(cell,conditionMessage(e));message(conditionMessage(e))
    if(kind=="boundary_paused")75L else 1L
  })
  quit(status=status)
}
