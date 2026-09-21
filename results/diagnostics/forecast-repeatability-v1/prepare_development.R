#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly=TRUE)
source("R/empirical.R")
stopifnot(getRversion() == "4.2.1", packageVersion("RSiena") == "1.3.10")
flag <- function(key,default=NULL) { i <- match(key,args); if(is.na(i)) default else args[i+1] }
out <- flag("--output","data")
dir.create(out,recursive=TRUE,showWarnings=FALSE)
dir.create(file.path(out,"past"),showWarnings=FALSE)
dir.create(file.path(out,"targets"),showWarnings=FALSE)
env <- new.env(); load(args[1],envir=env)
dat <- env$dat; rm(env); gc()
required <- c("ccode1","ccode2","year",NET_DV,BEH_DV,"contig_d",setdiff(MONADIC,"milexSpLag_1"),DYADIC)
dat <- as.data.frame(dat[required]); gc()
dat <- dat[dat$year <= 2009L, , drop=FALSE]; gc()
if(!all(1990:2009 %in% unique(dat$year))) stop("Annual observations do not support prespecified years")
audit <- list(years=sort(unique(dat$year)),preprocessing_version=MODEL_VERSION,targets=list())
# Target packets are written by this trusted preparation process. Predictor
# reads only the separately materialized past packet, never this raw archive.
for(t in 2006:2009) {
  packet <- build_past_data(dat,1990:(t-1L))
  saveRDS(packet,file.path(out,"past",paste0(t,".rds")))
  target <- dat[dat$year==t,,drop=FALSE]
  ids <- sort(unique(c(target$ccode1,target$ccode2)))
  mat <- matrix(NA_real_,length(ids),length(ids),dimnames=list(as.character(ids),as.character(ids)))
  mat[cbind(match(target$ccode1,ids),match(target$ccode2,ids))] <- target[[NET_DV]]
  diag(mat)<-NA_real_
  beh <- unique(target[c("ccode1",BEH_DV)])
  if(anyDuplicated(beh$ccode1)) stop("Target behavior inconsistent")
  b <- as.numeric(cut(beh[[BEH_DV]],c(seq(0,.1,.01),1),labels=1:11,right=FALSE))
  names(b) <- as.character(beh$ccode1)
  saveRDS(list(nms=ids,network=mat,behavior=unname(b[as.character(ids)]),target=t,present=rep(TRUE,length(ids))),file.path(out,"targets",paste0(t,".rds")))
  # This report contains provenance/coverage, never target labels or tie counts.
  audit$targets[[as.character(t)]] <- list(training_years=range(packet$years),actors=length(packet$nms),
    actors_present_at_origin=sum(packet$present[,ncol(packet$present)]),
    training_network_missing=sum(is.na(packet$data[[NET_DV]])),
    training_behavior_missing=sum(is.na(packet$data[[BEH_DV]])),
    training_behavior_range=range(packet$data[[BEH_DV]],na.rm=TRUE),
    composition_changes=lapply(which(vapply(packet$data$comp,function(x)!identical(as.integer(x),c(1L,length(packet$years))),logical(1))),
      function(i) list(ccode=packet$nms[i],presence_waves=packet$data$comp[[i]])))
  rm(packet); gc()
}
write_json(audit,file.path(out,"preparation_audit.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
cat("Prepared past-only packets and separate target packets. No forecasting or scoring performed.\n")
