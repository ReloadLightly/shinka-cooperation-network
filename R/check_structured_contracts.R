#!/usr/bin/env Rscript
# Synthetic native regression fixture, NOT estimation or scientific fitness.
# Run from the repository root in the existing R 4.2.1 / RSiena 1.3.10 runtime.
stopifnot(as.character(getRversion()) == "4.2.1")
source("R/forecast.R")
source("R/network_specification_v2.R")
stopifnot(as.character(packageVersion("RSiena")) == "1.3.10")
N <- 161L; T <- 3L
ids <- seq_len(N); waves <- seq_len(T)
a <- array(0, c(N,N,T))
for(t in waves) {
  m <- outer(ids,ids,function(i,j)as.numeric((i+j+t)%%31L==0L))
  diag(m) <- 0; a[,,t] <- m
}
d <- list(); d[[NET_DV]] <- a
z <- outer(ids,waves,function(i,t)as.numeric(1L+(i+2L*t)%%11L))
d[[BEH_DV]] <- z
for(v in MONADIC)d[[paste0("m.",v)]] <- outer(ids,waves,function(i,t)sin(i/17)+t/10)
for(v in DYADIC) {
  x <- array(0,c(N,N,T))
  for(t in waves) {x[,,t] <- outer(ids,ids,function(i,j)abs(i-j)/N+t/100);diag(x[,,t]) <- 0}
  d[[paste0("d.",v)]] <- x
}
d$comp <- rep(list(c(1L,T)),N);d$comp[[N]] <- c(1L,2L)
present <- matrix(TRUE,N,T);present[N,T] <- FALSE
packet <- list(data=d,years=2001:2003,nms=ids,present=present)
train <- make_training_data(packet)
forward <- make_forward_data(packet,train)
atom <- function(effect,parameter=0L,...)list(effect=effect,parameter=parameter,...)
base <- list(schema_version=2L,network_effects=list(atom("degPlus",1L),atom("transTriads")))
old <- model_effects(train,c("degPlus","transTriads"))
new <- build_network_effects_v2(train,base)$effects

# Synthetic coefficient object is only a fixture for mapping/transformation.
# It is never saved as an accepted empirical fit or sent to the evaluator.
fixture_fit <- function(effects) {
  requested <- effects[effects$include,,drop=FALSE]
  requested <- do.call(rbind,lapply(unique(requested$name),function(name)requested[requested$name==name,,drop=FALSE]))
  theta <- rep(0,nrow(requested));theta[requested$type=="rate"] <- .2
  theta[requested$name=="dv.net"&requested$shortName=="density"] <- -4
  theta[requested$shortName=="degPlus"] <- -.001
  theta[requested$shortName=="transTriads"] <- .05
  theta[requested$name=="milex.beh"&requested$shortName=="linear"] <- -.1
  theta[requested$name=="milex.beh"&requested$shortName=="quad"] <- -.05
  structure(list(requestedEffects=requested,theta=theta,effects=effects,gmm=FALSE,cconditional=FALSE),class="sienaFit")
}
f <- fixture_fit(old)
tagged <- v2_adopt_legacy_fit(f,new,base)
updated <- v2_update_theta(new,tagged)
stopifnot(identical(f$theta,tagged$theta),all(is.finite(updated$initialValue[updated$include])))
reordered <- tagged; reordered$requestedEffects <- reordered$requestedEffects[nrow(reordered$requestedEffects):1,,drop=FALSE]
stopifnot(inherits(try(v2_update_theta(new,reordered),silent=TRUE),"try-error"))
legacy_forward <- forward_effects(forward,train,f,c("degPlus","transTriads"))
structured_forward <- forward_effects_v2(forward,train,tagged,base)
coefficient_table <- function(e) {
  e <- e[e$include,,drop=FALSE]
  out <- data.frame(key=effect_key(e),value=e$initialValue)
  out <- out[order(out$key),,drop=FALSE];rownames(out) <- NULL;out
}
stopifnot(isTRUE(all.equal(coefficient_table(legacy_forward$effects),coefficient_table(structured_forward$effects),tolerance=1e-12)))

# Native parameter instances and dynamic-operand recentering.
product <- list(product=list(atom("gwesp",69L),atom("egoX",0L,covariate="milex.beh")))
extended <- list(schema_version=2L,network_effects=list(atom("gwesp",69L),atom("gwesp",100L),product))
built <- build_network_effects_v2(train,extended)
fit <- fixture_fit(built$effects)
key69 <- paste0("network|",v2_term_key(atom("gwesp",69L)))
key100 <- paste0("network|",v2_term_key(atom("gwesp",100L)))
keyproduct <- paste0("network|",v2_term_key(v2_term(product)))
set_coefficient <- function(key,value) {i <- match(key,fit$requestedEffects$.spec_key);stopifnot(!is.na(i));fit$theta[i] <<- value}
set_coefficient(key69,.2);set_coefficient(key100,-.1);set_coefficient(keyproduct,.03)
fwd <- forward_effects_v2(forward,train,fit,extended)
get_coefficient <- function(key) fwd$effects$initialValue[match(key,fwd$effects$.spec_key)]
stopifnot(abs(get_coefficient(key69)-(.2+.03*fwd$mean_shift))<1e-12,
          abs(get_coefficient(key100)-(-.1))<1e-12,
          abs(get_coefficient(keyproduct)-.03)<1e-12)

# Force BOTH native entry points; no empirical cache can mask adapter defects.
# Four synthetic endpoints are a mechanics check, not an altered evaluation budget.
work <- tempfile("structured-contracts-");dir.create(work)
simulate <- function(effects,runner,label) {
  alg <- sienaAlgorithmCreate(projname=file.path(work,label),cond=FALSE,useStdInits=FALSE,
    nsub=0,n3=4L,seed=4567L,modelType=c(dv.net=3),behModelType=c(milex.beh=1),simOnly=TRUE)
  runner(alg,data=forward$netdata,effects=effects,batch=TRUE,silent=TRUE,useCluster=FALSE,returnDeps=TRUE)$sims
}
old_sims <- simulate(legacy_forward$effects,siena07,"legacy")
new_sims <- simulate(structured_forward$effects,v2_native_runner(),"structured")
stopifnot(length(old_sims)==4L,identical(old_sims,new_sims))
cat("PASS: synthetic native allocation, identity ordering, parameter mapping, recentering and forced legacy/structured endpoint equivalence. No estimation or empirical outcomes.\n")
unlink(work,recursive=TRUE)
