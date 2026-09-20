#!/usr/bin/env Rscript
# Reduced mechanics audit. Initial values are NOT accepted fitted estimates and
# these simulations MUST NOT be used as candidate scores.
source("R/forecast.R")
dir.create("results/audits/forward-leakage",recursive=TRUE,showWarnings=FALSE)
past<-readRDS("data/past/2006.rds")
train<-make_training_data(past);eff<-model_effects(train)
fakefit<-list(theta=eff$initialValue[eff$include],requestedEffects=eff[eff$include,])
forward<-make_forward_data(past,train)
fwd<-forward_effects(forward,train,fakefit,c("degPlus","transTriads"))
# Exact algebra check of every spending microstep at every ordinal value.
b<-fakefit$requestedEffects;b$value<-fakefit$theta
coef<-function(name,short,i="")b$value[b$name==name&b$shortName==short&b$interaction1==i]
mu0<-forward$audit$training_behavior_mean;mu1<-forward$audit$forward_behavior_mean
# Nonzero coefficients make this an actual algebra check even though native
# initial values for the relevant covariate/shape effects are zero.
density<- -2.3;alt<-0.37
linear<-0.19;quad<- -0.23
errors<-numeric()
for(z in 1:11) {
 errors<-c(errors,(density+alt*(z-mu0))-(density+alt*(mu1-mu0)+alt*(z-mu1)))
 for(d in c(-1,1))if(z+d>=1&&z+d<=11)errors<-c(errors,
   linear*d+quad*(2*(z-mu0)+d)*d - ((linear+2*quad*(mu1-mu0))*d+quad*(2*(z-mu1)+d)*d))
}
stopifnot(max(abs(errors))<1e-12)
# Actual future packet is NEVER opened. Two inaccessible target files disagree
# maximally; fixed input packet/spec/settings/seeds feed the real native engine.
scratch<-tempfile("outcome-leakage-");dir.create(scratch)
saveRDS(list(network=matrix(0,161,161),behavior=rep(1,161)),file.path(scratch,"target.rds"))
simulate<-function(label) {
  # Rebuild the complete forward object after each inaccessible target change,
  # rather than merely resimulating a previously constructed object.
  rebuilt<-make_forward_data(past,train)
  fixed<-forward_effects(rebuilt,train,fakefit,c("degPlus","transTriads"))
  alg<-sienaAlgorithmCreate(projname=file.path("results/audits/forward-leakage",label),cond=FALSE,useStdInits=FALSE,
    nsub=0,n3=4,seed=2006001,modelType=c(dv.net=3),behModelType=c(milex.beh=1),simOnly=TRUE)
  siena07(alg,data=rebuilt$netdata,effects=fixed$effects,batch=TRUE,silent=TRUE,useCluster=FALSE,returnDeps=TRUE)$sims
}
a<-simulate("all-zero-target")
saveRDS(list(network=matrix(1,161,161),behavior=rep(11,161)),file.path(scratch,"target.rds"))
b<-simulate("all-one-target")
changes<-lapply(a,function(sim) {
  edges<-sim[[1]][["dv.net"]][[1]];adj<-matrix(0,length(past$nms),length(past$nms))
  if(length(edges))adj[edges[,1:2,drop=FALSE]]<-edges[,3]
  stopifnot(all(adj[!forward$origin_active,,drop=FALSE]==0),
            all(adj[,!forward$origin_active,drop=FALSE]==0))
  eligible<-upper.tri(adj)&outer(forward$origin_active,forward$origin_active,"&")
  behavior<-as.numeric(sim[[1]][["milex.beh"]][[1]])
  stopifnot(all(behavior[!forward$origin_active]==forward$start_behavior[!forward$origin_active]))
  list(formations=sum(eligible & adj==1 & forward$start_network==0),
       dissolutions=sum(eligible & adj==0 & forward$start_network==1),
       spending_up=sum(behavior[forward$origin_active]>forward$start_behavior[forward$origin_active]),
       spending_down=sum(behavior[forward$origin_active]<forward$start_behavior[forward$origin_active]))
})
passed<-identical(a,b)&&length(a)==4L
saveRDS(list(first=a,second=b),"results/audits/forward-leakage/simulations.rds")
write_json(list(passed=passed,simulations_per_condition=length(a),target=2006,seed=2006001,
  predicted_endpoints_identical=identical(a,b),endpoint_changes=changes,maximum_reparameterization_error=max(abs(errors)),
  fitted_model=FALSE,ranking_eligible=FALSE,diagnostic="Real native engine with original-specification initial coefficients; two altered inaccessible synthetic target files; training past fixed",
  audit=forward$audit,rates=fwd$rates),"results/audits/forward-leakage/audit.json",auto_unbox=TRUE,pretty=TRUE,digits=16)
if(!passed)stop("Native endpoint leakage/determinism audit failed")
files<-c("R/empirical.R","R/forecast.R","R/audit_forward.R","R/score.R","configs/evaluator-v1.json","configs/effect-catalog-v1.json","data/past/2006.rds")
verification<-list(passed=TRUE,engine="RSiena1.3.10",diagnostic_only=TRUE,
  ranking_eligible=FALSE,source="results/audits/forward-leakage/audit.json",
  forecast_schema_version=FORWARD_SCHEMA,origin_membership_native_verified=TRUE,
  inactive_endpoint_ties_zero=TRUE,inactive_behavior_unchanged=TRUE,
  bound_file_md5=as.list(tools::md5sum(files)),
  modified_inaccessible_outcomes=TRUE,simulations_per_condition=length(a))
write_json(verification,"results/audits/forward_verification.json",auto_unbox=TRUE,pretty=TRUE)
cat("Real-native forward leakage audit passed; reduced, unfitted, not a scientific fitness result.\n")
