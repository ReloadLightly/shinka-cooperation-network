#!/usr/bin/env Rscript
# Execute the authors' original data builder and predictive specification prefix,
# without running estimation or importing target-year outcomes into a fit.
suppressPackageStartupMessages({library(dplyr);library(tidyr);library(reshape2);library(igraph);library(sna)})
source("R/empirical.R")
dir.create("results/audits",recursive=TRUE,showWarnings=FALSE)
root<-normalizePath(".");author<-new.env(parent=globalenv())
author$wd<-file.path(root,"sources/original/IO_Final")
author$yr<-1990:2005;author$yrlo<-1990:2004;author$thi<-16;author$tlo<-15
# All appendix inputs are retained in this independent reference execution.
author$dv.use<-NET_DV;author$bdv.use<-BEH_DV;author$bdv.uniform<-FALSE;author$levs<-11
 author$m.cons<-c(MONADIC,"allySpillin_1","loans_1","triangles_1","degree_1","trisUNGA_1","ideal_1")
author$d.cons<-c(DYADIC,"loan_d");author$ds<-1:5;author$ms1<-c(1,7);author$ms2<-c(1,2,3,4,5,6,8)
author$seed<-12345
# Memory-only harness adaptation: drop unused raw columns immediately after
# base::load, preserving all rows and all values the unchanged script can use.
author$load <- function(file) {
  raw<-new.env();base::load(file,envir=raw)
  columns<-unique(c("ccode1","ccode2","year",NET_DV,BEH_DV,"contig_d",DYADIC,
    setdiff(MONADIC,"milexSpLag_1"),"loans_1","loan_d","ideal_1"))
  assign("dat",raw$dat[columns],envir=parent.frame());rm(raw);gc();invisible("dat")
}
old<-setwd(author$wd)
sys.source("scripts/00.buildDataset",envir=author)
rm(list=c("dat"),envir=author); gc()
code<-readLines("scripts/00.gof.predict")
end<-which(code=="## Estimate it")[1]-1
if(!is.finite(end))stop("Original source boundary not found")
eval(parse(text=code[seq_len(end)]),envir=author)
setwd(old)
rm(list=setdiff(ls(author),c("data","effs")),envir=author); gc()
packet<-readRDS("data/past/2006.rds")
bridge<-make_training_data(packet);effs<-model_effects(bridge)
checks<-list()
for(v in c(NET_DV,BEH_DV,paste0(BEH_DV,".orig")))checks[[v]]<-isTRUE(all.equal(author$data[[v]],packet$data[[v]],check.attributes=FALSE))
for(v in MONADIC)checks[[paste0("m.",v)]]<-isTRUE(all.equal(author$data[[paste0("m.",v)]],packet$data[[paste0("m.",v)]][,1:15],check.attributes=FALSE))
for(v in DYADIC)checks[[paste0("d.",v)]]<-isTRUE(all.equal(author$data[[paste0("d.",v)]],packet$data[[paste0("d.",v)]][,,1:15],check.attributes=FALSE))
checks$composition<-isTRUE(all.equal(author$data$comp,packet$data$comp,check.attributes=FALSE))
a<-author$effs[author$effs$include,];b<-effs[effs$include,]
# Rates share names/periods, effects internal parameters and initial values.
key<-function(x)paste(effect_key(x),x$period,sep="|")
a<-a[order(key(a)),];b<-b[order(key(b)),]
cols<-c("name","shortName","type","interaction1","interaction2","parm","period","initialValue","fix")
checks$effect_specification<-isTRUE(all.equal(a[,cols],b[,cols],check.attributes=FALSE))
write.csv(a[,cols],"results/audits/author_predictive_effects.csv",row.names=FALSE)
write.csv(b[,cols],"results/audits/bridge_predictive_effects.csv",row.names=FALSE)
write_json(list(passed=all(unlist(checks)),training_years=c(1990,2005),checks=checks,
  reference="untouched 00.buildDataset and 00.gof.predict prefix through Model 3 effect construction",
  note="Original source builder/effect code unchanged; harness load wrapper drops unused raw columns immediately after base::load to reduce memory, retaining all source rows and used values. Reference audit only, no candidate access."),
  "results/audits/source_parity.json",auto_unbox=TRUE,pretty=TRUE)
if(!all(unlist(checks))) {print(checks);stop("Source parity failed")}
cat("Source preparation and predictive Model 3 effects match independent bridge.\n")
