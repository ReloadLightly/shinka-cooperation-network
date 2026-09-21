# Read-only correction of finite-batch NETWORK probability pooling. No fitting,
# forecasting, simulation or target-packet reads. Uses original PRROC scorer and
# labels/masks already recorded in Step 4's scored evidence. Spending means and
# stored RMSEs are unchanged: this version changes only binary-network pooling.
source("R/step4_compare.R")
source("R/score.R")
network_count_pool <- function(predictions,indices) {
  n<-vapply(predictions[indices],function(p)as.integer(p$simulations),integer(1))
  assert(all(n==1000L),"Every batch must contain 1000 endpoints")
  counts<-lapply(predictions[indices],function(p){
    x<-p$probabilities*1000L
    assert(all(is.finite(x))&&max(abs(x-round(x)))<1e-8,"Probability is not a count/1000")
    round(x)
  })
  Reduce(`+`,counts)/sum(n)
}
score_view <- function(cell,out,model,year) {
  pp<-lapply(1:5,function(b)readRDS(file.path(cell,"forecasts",b,"predictions.rds")))
  old<-read_json(file.path(cell,"scores/comparison-metrics.json"),simplifyVector=FALSE)
  tables<-lapply(1:5,function(b)read.csv(file.path(cell,"scores",b,"eligibility_and_scores.csv"),stringsAsFactors=FALSE))
  keys<-c("ccode1","ccode2","eligible","origin","label")
  for(t in tables)assert(identical(t[keys],tables[[1]][keys]),"Stored labels or masks differ across batches")
  t<-tables[[1]]; ids<-as.character(pp[[1]]$nms)
  coords<-cbind(match(as.character(t$ccode1),ids),match(as.character(t$ccode2),ids))
  assert(!anyNA(coords),"Saved score row refers to another population")
  for(b in 1:5){
    assert(identical(pp[[b]]$nms,pp[[1]]$nms),"Forecast populations differ")
    assert(max(abs(pp[[b]]$probabilities[coords]-tables[[b]]$probability))<1e-14,"Saved scored and native predictions disagree")
    a<-curve_metrics(tables[[b]]$probability[t$eligible],t$label[t$eligible])$pr_auc
    assert(abs(a-old$batches[[b]]$pr_auc)<1e-13,"Original batch PRROC cannot be reproduced")
  }
  metric<-function(probs,base){
    p<-probs[coords][t$eligible];y<-t$label[t$eligible];origin<-t$origin[t$eligible]
    base$pr_auc<-curve_metrics(p,y)$pr_auc
    base$brier<-mean((p-y)^2)
    base$formation_pr_auc<-curve_metrics(p[origin==0],y[origin==0])$pr_auc
    base$dissolution_pr_auc<-curve_metrics(1-p[origin==1],1-y[origin==1])$pr_auc
    base
  }
  legacy<-metric(Reduce(`+`,lapply(pp,`[[`,"probabilities"))/5,old$pooled)
  assert(max(abs(unlist(legacy)-unlist(old$pooled)))<1e-13,"Original pooled score cannot be reproduced")
  corrected<-old;corrected$pooled<-metric(network_count_pool(pp,1:5),old$pooled)
  for(b in 1:5)corrected$delete_one_batch[[b]]<-metric(network_count_pool(pp,setdiff(1:5,b)),old$delete_one_batch[[b]])
  record<-list(version="integer-network-count-pooling-v1",source_commit="104ba59d81a92f1c98b77c89178fad9178b6ccb4",
    source_cell_commitment=precision_sha(file.path(cell,"cell-commitment.json")),model=model,year=year,
    correction_source_sha256=precision_sha("R/replicated_score_view.R"),metrics=corrected,
    original_pooled=old$pooled,new_fits=0L,new_forecasts=0L,new_simulations=0L,target_packets_read=0L,
    statement="Read-only rescore of saved native forecasts. Preserve mathematically equal pooled binary probabilities by summing integer successes before dividing. Original Step 4 evidence untouched. Spending pooling/RMSE unchanged.")
  dir.create(out,recursive=TRUE,showWarnings=FALSE)
  precision_json(record,file.path(out,paste0(model,"-",year,".json")))
  record
}
if(sys.nframe()==0L) {
  args<-commandArgs(trailingOnly=TRUE)
  assert(length(args)==2L,"Need saved evidence root and separate output folder")
  assert(as.character(getRversion())=="4.2.1"&&as.character(packageVersion("RSiena"))=="1.3.10","Wrong native runtime")
  for(m in c("reference","gwesp69"))for(y in 2006:2009) {
    cell<-file.path(args[1],"results/step4-closure-comparison-v1",m,y)
    x<-score_view(cell,args[2],m,y)
    cat(m,y,"legacy",x$original_pooled$pr_auc,"integer pooled",x$metrics$pooled$pr_auc,"\n")
  }
}
