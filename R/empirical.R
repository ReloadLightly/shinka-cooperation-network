# Trusted empirical Model 3 adapter for RSiena 1.3.10.
# Candidate programs provide only validated network-effect identifiers.
suppressPackageStartupMessages(library(RSiena))
suppressPackageStartupMessages(library(jsonlite))
MODEL_VERSION <- "model3-bridge-v1"
NET_DV <- "dcaGeneralV1_d"
BEH_DV <- "milexPerGDP_1"
MONADIC <- c("democracy_1", "GDPgrowth_1", "nato_1", "allies_1", "military_1", "lnmids_1", "lncinc_1", "milexSpLag_1")
DYADIC <- c("ATOP_d", "lndistance_d", "absidealdiff_d", "lntrade_d", "NATO_d")
SUPPORTED <- c("degPlus", "transTriads", "inPop", "gwesp")

validate_spec <- function(spec) {
  stopifnot(identical(sort(names(spec)), sort(c("schema_version", "network_effects"))))
  stopifnot(spec$schema_version == 1)
  terms <- unlist(spec$network_effects, use.names=FALSE)
  if (length(terms) > 3 || anyDuplicated(terms) || any(!terms %in% SUPPORTED)) stop("Invalid network-effect catalog or complexity")
  sort(terms)
}

# Base-R reconstruction, cross-checked against authors' unchanged builder.
# The caller must pass ONLY observations at or before the forecast origin.
build_past_data <- function(dat, years) {
  dat <- dat[dat$year %in% years, , drop=FALSE]
  nms <- unique(dat$ccode1)
  nms <- intersect(nms, unique(dat$ccode1[!is.na(dat[[BEH_DV]])]))
  dat <- dat[dat$ccode1 %in% nms & dat$ccode2 %in% nms, , drop=FALSE]
  if (!identical(as.numeric(nms), sort(as.numeric(nms)))) stop("Author actor ordering is not sorted; parity review required")
  N <- length(nms); T <- length(years)
  dm <- list(as.character(nms), as.character(nms), as.character(years))
  data <- list()
  data[[NET_DV]] <- array(NA_real_, c(N,N,T), dimnames=dm)
  data[[BEH_DV]] <- matrix(NA_real_,N,T,dimnames=dm[c(1,3)])
  data[[paste0(BEH_DV,".orig")]] <- data[[BEH_DV]]
  for (v in MONADIC) data[[paste0("m.",v)]] <- data[[BEH_DV]]
  for (v in DYADIC) data[[paste0("d.",v)]] <- data[[NET_DV]]
  present <- matrix(FALSE,N,T,dimnames=dm[c(1,3)])
  for (k in seq_along(years)) {
    d <- dat[dat$year == years[k],,drop=FALSE]
    ij <- cbind(match(d$ccode1,nms),match(d$ccode2,nms))
    present[,k] <- nms %in% unique(d$ccode1)
    for (v in c(NET_DV,DYADIC,"contig_d")) {
      mat <- matrix(NA_real_,N,N,dimnames=dm[1:2]); mat[ij] <- d[[v]]; diag(mat) <- 0
      if (v %in% DYADIC && !isSymmetric(mat)) mat <- sna::symmetrize(mat,rule="weak")
      if (v == NET_DV) data[[v]][,,k] <- mat
      else if (v %in% DYADIC) data[[paste0("d.",v)]][,,k] <- mat
      else contig <- mat
    }
    mono <- unique(d[c("ccode1",BEH_DV,setdiff(MONADIC,"milexSpLag_1"))])
    if (anyDuplicated(mono$ccode1)) stop("Inconsistent monadic values within country-year")
    mi <- match(mono$ccode1,nms)
    rawbeh <- rep(NA_real_,N); rawbeh[mi] <- mono[[BEH_DV]]
    data[[paste0(BEH_DV,".orig")]][,k] <- rawbeh
    data[[BEH_DV]][,k] <- as.numeric(cut(rawbeh,c(seq(0,0.1,0.01),1),labels=1:11,right=FALSE))
    for (v in setdiff(MONADIC,"milexSpLag_1")) data[[paste0("m.",v)]][mi,k] <- mono[[v]]
    # Match the author's year-specific universe before multiplication: actors
    # absent from that year must not create all-NA rows in its contiguity matrix.
    active <- which(present[,k]); w <- contig[active,active,drop=FALSE]
    w <- w / rowSums(w); w[is.nan(w)] <- 0
    z <- rawbeh[active]; z[is.na(z)] <- 0
    data[["m.milexSpLag_1"]][active,k] <- as.vector(w %*% z)
  }
  comp <- lapply(seq_len(N), function(i) range(which(present[i,])))
  names(comp) <- as.character(nms); data$comp <- comp
  list(data=data, years=years, nms=nms, present=present,
       preprocessing_version=MODEL_VERSION)
}

make_training_data <- function(packet) {
  d <- packet$data; T <- length(packet$years)
  args <- list(dv.net=sienaDependent(d[[NET_DV]],type="oneMode"),
               milex.beh=sienaDependent(d[[BEH_DV]],type="behavior"))
  for (v in MONADIC) args[[paste0("beh.",v)]] <- varCovar(d[[paste0("m.",v)]][,seq_len(T-1),drop=FALSE])
  for (v in DYADIC) {
    a <- d[[paste0("d.",v)]]
    args[[paste0("nets.",v)]] <- if(v=="lndistance_d") coDyadCovar(a[,,T-1]) else varDyadCovar(a[,,seq_len(T-1),drop=FALSE])
  }
  args$cc <- sienaCompositionChange(d$comp)
  do.call(sienaDataCreate,args)
}

model_effects <- function(netdata, terms=c("degPlus","transTriads")) {
  effs <- getEffects(netdata)
  for (v in DYADIC) effs <- includeEffects(effs,X,interaction1=paste0("nets.",v),type="eval",name="dv.net",verbose=FALSE)
  for (v in c("beh.democracy_1","beh.lncinc_1","milex.beh")) effs <- includeEffects(effs,altX,interaction1=v,type="eval",name="dv.net",verbose=FALSE)
  for (v in MONADIC[c(1,2,3,4,5,6,8)]) effs <- includeEffects(effs,effFrom,interaction1=paste0("beh.",v),type="eval",name="milex.beh",verbose=FALSE)
  effs <- includeEffects(effs,outdeg,interaction1="dv.net",type="eval",name="milex.beh",verbose=FALSE)
  effs <- setEffect(effs,behDenseTriads,interaction1="dv.net",type="eval",name="milex.beh",parameter=6,verbose=FALSE)
  for (v in terms) {
    ix <- which(effs$name=="dv.net" & effs$type=="eval" & effs$shortName==v & effs$interaction1=="" & effs$interaction2=="")
    if(length(ix)!=1) stop("Unsupported/ambiguous native effect: ",v)
    effs$include[ix] <- TRUE
    expected_parameter <- c(degPlus=1,transTriads=0,inPop=0,gwesp=69)[[v]]
    if(effs$parm[ix] != expected_parameter) stop("Unexpected native effect parameter for ",v)
  }
  effs
}

effect_key <- function(effs) paste(effs$name,effs$type,effs$shortName,effs$interaction1,effs$interaction2,effs$parm,sep="|")

fit_diagnostics <- function(fit, expected_n3=1000L) {
  estimates <- as.numeric(fit$theta); p <- length(estimates)
  ratios <- as.numeric(fit$tconv); covariance <- fit$covtheta
  covariance_shape <- p>0L && is.matrix(covariance) && identical(dim(covariance),c(p,p))
  covariance_finite <- covariance_shape && all(is.finite(covariance))
  se <- if(covariance_shape) suppressWarnings(sqrt(diag(covariance))) else numeric()
  native_ok <- isTRUE(fit$OK) && identical(fit$termination,"OK")
  # fixed/diver normally have one element per requested parameter. newfixed
  # is absent in ordinary 1.3.10 fits. A scalar FALSE means no flags; a scalar
  # TRUE is invalid without inventing a list of supposedly affected effects.
  flags <- function(x,required=FALSE) {
    if(is.null(x)) return(list(present=FALSE,shape_valid=!required,any=FALSE,indices=integer()))
    valid <- is.logical(x) && !anyNA(x) && (length(x)==p || (length(x)==1L && !x))
    list(present=TRUE,shape_valid=isTRUE(valid),any=any(x %in% TRUE),
         indices=if(length(x)==p) which(x %in% TRUE) else integer())
  }
  divergence <- flags(fit$diver,required=TRUE)
  fixed <- flags(fit$fixed,required=TRUE)
  newly_fixed <- flags(fit$newfixed)
  flags_valid <- all(vapply(list(divergence,fixed,newly_fixed),function(x)x$shape_valid&&!x$any,logical(1)))
  covariance_message <- paste(as.character(fit$errorMessage.cov),collapse=" ")
  phase3_complete <- !isTRUE(fit$Phase3Interrupt) && is.matrix(fit$sf) &&
    nrow(fit$sf)==expected_n3 && length(fit$Phase3nits)==1L && fit$Phase3nits==expected_n3
  finite <- p>0L && length(ratios)==p && length(se)==p && all(is.finite(ratios)) &&
    all(is.finite(estimates)) && covariance_finite && all(is.finite(se)) && all(se>0)
  overall <- if(length(fit$tconv.max)==1L) as.numeric(fit$tconv.max) else NA_real_
  eigenvalues <- if(covariance_finite) eigen((covariance+t(covariance))/2,symmetric=TRUE,only.values=TRUE)$values else numeric()
  # Eigenvalues/condition number are diagnostics, not a scale-dependent new
  # rejection threshold. Native phase3 already checks statistic covariance.
  identified <- finite && flags_valid && !nzchar(covariance_message)
  list(valid=isTRUE(native_ok && phase3_complete && identified && max(abs(ratios))<0.1 &&
                     is.finite(overall) && overall<0.25),
       maximum_absolute_t_ratio=if(length(ratios)) max(abs(ratios)) else NA_real_,
       overall_maximum_convergence=overall,
       t_ratios=ratios, estimates=estimates, standard_errors=se,
       native_ok=native_ok, termination=as.character(fit$termination),
       phase3_complete=isTRUE(phase3_complete),
       phase3_iterations=if(length(fit$Phase3nits)==1L)fit$Phase3nits else NA_integer_,
       covariance_all_finite=covariance_finite,covariance_message=covariance_message,
       divergence=divergence,fixed_parameters=fixed,newly_fixed_parameters=newly_fixed,
       covariance_minimum_eigenvalue=if(length(eigenvalues))min(eigenvalues)else NA_real_,
       covariance_condition_number=if(covariance_finite)kappa(covariance,exact=TRUE)else NA_real_,
       finite_identified=identified)
}

fit_model <- function(netdata,effs,settings,outdir) {
  prev <- NULL; diagnostics <- list()
  prior_path <- file.path(outdir,"fit_diagnostics.json")
  prior <- if(file.exists(prior_path)) read_json(prior_path,simplifyVector=FALSE) else list()
  for (attempt in seq_len(settings$estimation$max_attempts %||% 3L)) {
    path <- file.path(outdir,paste0("fit-attempt-",attempt,".rds"))
    if(!file.exists(path)) break
    cached <- readRDS(path)
    diagnostics[[attempt]] <- if(length(prior)>=attempt) prior[[attempt]] else c(list(attempt=attempt),fit_diagnostics(cached,settings$estimation$n3 %||% 1000L))
    current <- fit_diagnostics(cached,settings$estimation$n3 %||% 1000L)
    for(n in names(current)) diagnostics[[attempt]][[n]] <- current[[n]]
    diagnostics[[attempt]]$resumed <- TRUE
    if(isTRUE(diagnostics[[attempt]]$valid)) return(list(fit=cached,diagnostics=diagnostics))
    prev <- cached
  }
  completed <- length(diagnostics)
  if(completed >= (settings$estimation$max_attempts %||% 3L)) stop("All fixed estimation attempts already failed; inspect archived diagnostics")
  for (attempt in seq.int(completed+1L,settings$estimation$max_attempts %||% 3L)) {
    alg <- sienaAlgorithmCreate(projname=file.path(outdir,paste0("fit-",attempt)),
      nsub=settings$estimation$nsub %||% 3, n3=settings$estimation$n3 %||% 1000,
      seed=(settings$estimation$seed %||% 12345) + attempt - 1L,
      modelType=c(dv.net=3),behModelType=c(milex.beh=1),cond=FALSE)
    started <- proc.time()
    fit <- siena07(alg,data=netdata,effects=effs,prevAns=prev,batch=TRUE,silent=TRUE,
                   useCluster=FALSE,returnDeps=FALSE)
    diagnostics[[attempt]] <- c(list(attempt=attempt,elapsed_seconds=unname((proc.time()-started)[3])),fit_diagnostics(fit,settings$estimation$n3 %||% 1000L))
    checkpoint <- file.path(outdir,paste0("fit-attempt-",attempt,".rds"))
    saveRDS(fit,paste0(checkpoint,".pending"));file.rename(paste0(checkpoint,".pending"),checkpoint)
    write_json(diagnostics,file.path(outdir,"fit_diagnostics.json"),auto_unbox=TRUE,pretty=TRUE,na="null",digits=16)
    if(isTRUE(diagnostics[[attempt]]$valid)) return(list(fit=fit,diagnostics=diagnostics))
    prev <- fit
  }
  stop("Estimation did not meet predeclared convergence/identification thresholds after fixed attempts; inspect fit_diagnostics.json")
}
`%||%` <- function(x,y) if(is.null(x)) y else x

effect_table <- function(e) as.data.frame(e[,vapply(e,function(x)!is.list(x),logical(1)),drop=FALSE])
