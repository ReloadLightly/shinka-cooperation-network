# Summarize only completed original-source calls. A subset is not full coverage.
suppressPackageStartupMessages({library(jsonlite);library(igraph)})
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=1L)stop("Usage: summarize_abm_checkpoints.R RUN_DIR")
out<-normalizePath(args[[1]])
files<-list.files(file.path(out,"checkpoints"),pattern="^call-.*[.]rds$",full.names=TRUE)
if(!length(files))stop("No completed native calls to summarize")
rows<-list();specifications<-list()
for(file in files) {
  result<-readRDS(file)$result
  effects<-result$requestedEffects
  fields<-intersect(c("name","shortName","type","interaction1","interaction2","parm","initialValue","fix"),names(effects))
  specifications[[basename(file)]]<-list(effects=effects[,fields,drop=FALSE],
      native_theta=result$theta,returned_simulations=length(result$sims))
  for(s in seq_along(result$sims)) {
    state<-result$sims[[s]][[1]]
    behavior<-as.numeric(state$milex.beh[[1]])
    n<-length(behavior)
    edges<-state$dv.net[[1]]
    a<-matrix(0,n,n)
    if(length(edges))a[edges[,1:2,drop=FALSE]]<-edges[,3]
    graph<-graph_from_adjacency_matrix(a,mode="undirected",diag=FALSE)
    rows[[length(rows)+1L]]<-data.frame(checkpoint=basename(file),simulation=s,
      countries=n,mean_spending_category=mean(behavior),
      density=igraph::edge_density(graph),clustering=igraph::transitivity(graph,type="globalundirected"),
      centralization=igraph::centr_eigen(graph,directed=FALSE,normalized=TRUE)$centralization,
      ties=sum(a[upper.tri(a)]))
  }
  rm(result);gc()
}
table<-do.call(rbind,rows)
write.csv(table,file.path(out,"endpoint_diagnostics.csv"),row.names=FALSE)
metrics<-c("mean_spending_category","density","clustering","centralization","ties")
summary<-lapply(split(table,table$checkpoint),function(x) {
  c(list(simulations=nrow(x),countries=unique(x$countries)),lapply(x[metrics],function(z)
    list(mean=mean(z),sd=sd(z),min=min(z),max=max(z),
         ci99=if(length(z)>1&&sd(z)>0)unname(t.test(z,conf.level=.99)$conf.int)else NULL)))
})
write_json(list(coverage="Completed checkpoint subset only; not full figure or equilibrium reproduction",
                checkpoints=length(files),results=summary,specifications=specifications),
           file.path(out,"endpoint_summary.json"),pretty=TRUE,auto_unbox=TRUE,digits=16)
cat("Summarized",nrow(table),"real native endpoints from",length(files),"completed calls.\n")
