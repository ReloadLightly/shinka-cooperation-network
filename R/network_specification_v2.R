# Structured extension only. Source R/forecast.R before this file.
# No installed RSiena source/namespace or legacy adapter is modified.
# Native references: data/allEffects.csv:197-241,423-451;
# R/initializeFRAN.r:574,643-651,2100-2119,2350-2396.
NETWORK_SPECIFICATION_VERSION <- "native-structured-network-v2"
V2_NETWORK_NODE_COUNT <- 161L
V2_STRUCTURAL <- c("degPlus","inPop","inPopSqrt","outAct","outActSqrt",
  "outTrunc","outInv","outSqInv","outInAss","transTriads","transTies",
  "gwesp","Jout","cycle4ND","nbrDist2","nbrDist2twice","between")
V2_MODIFIERS <- c("egoX","altX","X")

v2_integer <- function(x) {
  is.numeric(x) && !is.logical(x) && length(x)==1L && is.finite(x) &&
    x>=0 && x<=.Machine$integer.max && x==floor(x)
}
v2_atom <- function(x,internal=FALSE) {
  if(!is.list(x)||is.null(names(x))||anyDuplicated(names(x))||
     !all(c("effect","parameter") %in% names(x))||
     !all(names(x) %in% c("effect","parameter","covariate"))) stop("Malformed native effect atom")
  e<-x$effect;p<-x$parameter
  if(!is.character(e)||length(e)!=1L||is.na(e)||!v2_integer(p)) stop("Effect name/integer parameter invalid")
  if(e=="outTrunc2")e<-"outTrunc"
  if(!e %in% c(V2_STRUCTURAL,V2_MODIFIERS,if(internal)"density")) stop("Unsupported native symmetric effect: ",e)
  if(e=="degPlus") {if(p<1)stop("degPlus parameter must be at least 1");p<-if(p>=2)2L else 1L}
  else if(e %in% c("outInAss","cycle4ND")) {if(!p %in% c(1,2))stop(e," requires parameter 1 or 2")}
  else if(e=="outTrunc") {
    # Native k >= N-1 has the protected density contribution on every feasible
    # toggle. This is a genuine-knot bound, not a mutable complexity budget.
    if(p<1||p>=V2_NETWORK_NODE_COUNT-1L)
      stop("outTrunc requires a genuine knot 1..",V2_NETWORK_NODE_COUNT-2L,
           " for the declared ",V2_NETWORK_NODE_COUNT,"-actor universe")
  }
  else if(e %in% c("outInv","outSqInv")) {if(p<1)stop(e," requires a positive integer parameter")}
  else if(e=="gwesp") {
    # GwespFunction.cpp uses exp(k/100) and 1-exp(-k/100). Reject
    # overflow or a rounded unit geometric factor, not negative fitness.
    if(!is.finite(exp(p/100))||1-exp(-p/100)>=1)stop("GWESP parameter is numerically degenerate in the native engine")
  } else if(e=="Jout")p<-69L # Native OutJaccardFunction does not use parm.
  else if(p!=0)stop(e," has no mutable native internal parameter; use 0")
  out<-list(effect=e,parameter=as.integer(p))
  if(e %in% V2_MODIFIERS) {
    v<-x$covariate
    allowed<-if(e=="X")paste0("nets.",DYADIC) else c(paste0("beh.",MONADIC),"milex.beh")
    if(!is.character(v)||length(v)!=1L||is.na(v)||!v %in% allowed)stop("Invalid native covariate reference for ",e)
    out$covariate<-v
  } else if("covariate" %in% names(x))stop("Structural effect cannot have a covariate reference")
  out
}
v2_atom_key <- function(x) paste(x$effect,x$parameter,x$covariate %||% "",sep="|")
# Match Python's compact sort_keys=True JSON order, including lexical integer
# order (parameter 10 precedes 2). Native instance identity still uses the full
# value, never a row number or the ordering of candidate source text.
v2_json_key <- function(x) {
  sort_fields<-function(value) {
    if(!is.list(value))return(value)
    if(!is.null(names(value)))value<-value[order(names(value),method="radix")]
    lapply(value,sort_fields)
  }
  as.character(jsonlite::toJSON(sort_fields(x),auto_unbox=TRUE,null="null",digits=NA))
}
v2_interaction_type <- function(x) {
  if(x$effect=="egoX")"ego" else if(x$effect %in% c("altX","X","gwesp","Jout"))"dyadic" else ""
}
v2_product_valid <- function(atoms) {
  types<-vapply(atoms,v2_interaction_type,character(1))
  n<-length(atoms);egos<-sum(types=="ego");dyads<-sum(types=="dyadic")
  (n==2L&&(egos>=1L||dyads==2L)) || (n==3L&&(egos>=2L||egos+dyads==3L))
}
v2_term <- function(x,internal=FALSE) {
  if(is.list(x)&&identical(names(x),"product")) {
    if(!is.list(x$product)||!length(x$product)%in%c(2L,3L))stop("Native products require exactly two or three atom operands")
    atoms<-lapply(x$product,v2_atom,internal=internal)
    atoms<-atoms[order(vapply(atoms,v2_json_key,character(1)),method="radix")]
    if(!v2_product_valid(atoms))stop("Native interaction requires an ego factor or all dyadic factors (two-way); two ego factors or all ego/dyadic (three-way)")
    # The native GWESP(0) contribution AND tie statistic are binary, so
    # repeating this factor is exactly idempotent. Preserve multiplicity for
    # every other factor; transTies does not have a binary contribution.
    zero_gwesp<-which(vapply(atoms,function(atom)
      atom$effect=="gwesp"&&atom$parameter==0L,logical(1)))
    if(length(zero_gwesp)>1L) {
      atoms<-atoms[-zero_gwesp[-1L]]
      if(length(atoms)==1L) {
        if(!internal&&atoms[[1]]$effect%in%V2_MODIFIERS)
          stop("A reduced product cannot introduce a standalone covariate modifier")
        return(atoms[[1]])
      }
      if(!v2_product_valid(atoms))stop("Reduced native product is incompatible")
    }
    return(list(product=unname(atoms)))
  }
  atom<-v2_atom(x,internal=internal)
  if(!internal&&atom$effect %in% V2_MODIFIERS)stop("Covariate modifiers are permitted only as product operands; original controls remain fixed")
  atom
}
v2_term_key <- function(x) {
  if(!is.null(x$product))paste0("product(",paste(vapply(x$product,v2_atom_key,character(1)),collapse=";"),")")
  else paste0("atom(",v2_atom_key(x),")")
}
validate_network_specification_v2 <- function(spec) {
  if(!is.list(spec)||!identical(sort(names(spec)),sort(c("schema_version","network_effects")))||
     !v2_integer(spec$schema_version)||spec$schema_version!=2L||!is.list(spec$network_effects))
    stop("Expected schema_version 2 and a network_effects array")
  terms<-lapply(spec$network_effects,v2_term)
  keys<-vapply(terms,v2_term_key,character(1))
  if(anyDuplicated(keys))stop("Duplicate canonical mathematical terms")
  atoms<-Filter(function(x)is.null(x$product),terms)
  raw<-sum(vapply(atoms,function(x)(x$effect=="degPlus"&&x$parameter==1L)||x$effect%in%c("inPop","outAct"),logical(1)))
  roots<-sum(vapply(atoms,function(x)(x$effect=="degPlus"&&x$parameter==2L)||x$effect%in%c("inPopSqrt","outActSqrt"),logical(1)))
  if(raw>1L||roots>1L)stop("Joint degree variants have proportional symmetric estimation moments; retain one alternative per raw/root group")
  closure<-sum(vapply(atoms,function(x)(x$effect=="gwesp"&&x$parameter==0L)||x$effect=="transTies",logical(1)))
  if(closure>1L)stop("GWESP(0) and transTies have identical native estimation moments; choose one actor-choice mechanism")
  # GWESP(0)'s indicator and transTies' critical-in-star contribution differ,
  # so retain separate scientific identities. Their per-ego statistics are
  # nevertheless identical, including with the same compatible ego factors.
  # This transformed key detects moment redundancy only; it is not canonical
  # model identity and never replaces either requested native operator.
  products<-Filter(function(term)!is.null(term$product),terms)
  moment_keys<-vapply(products,function(term) {
    factors<-lapply(term$product,function(atom) {
      if(atom$effect=="gwesp"&&atom$parameter==0L)list(effect="transTies",parameter=0L)else atom
    })
    factors<-factors[order(vapply(factors,v2_json_key,character(1)),method="radix")]
    v2_json_key(list(product=unname(factors)))
  },character(1))
  if(anyDuplicated(moment_keys))stop("GWESP(0) and transTies products with identical compatible ego factors have identical estimation moments; choose one interaction")
  list(schema_version=2L,network_effects=unname(terms[order(vapply(terms,v2_json_key,character(1)),method="radix")]))
}

# The key is independent of native effect numbers and includes every operand.
# Rate keys additionally retain group/period identity. All rows get a key so
# parameter-aware native retries do not lose mandatory spending/control terms.
v2_native_base_key <- function(e) paste(e$name,e$type,e$shortName,e$interaction1,
  e$interaction2,e$parm,e$group,e$period,sep="|")
v2_native_row_atom <- function(row) {
  e<-as.character(row$shortName)
  if(row$name!="dv.net"||row$type!="eval"||row$interaction2!=""||
     !e%in%c(V2_STRUCTURAL,V2_MODIFIERS,"outTrunc2","density"))return(NULL)
  parameter<-as.integer(row$parm)
  # allEffects' template metadata need not use our canonical spelling for an
  # ignored native parameter. These families do not consult parm in the
  # selected factory branch (egoX/altX have threshold flags disabled). Index
  # their mathematical atom at 0 without changing the native template row.
  # Strict saved-fit matching below still compares the original native parm.
  ignored<-c("density","inPop","inPopSqrt","outAct","outActSqrt",
    "transTriads","transTies","between","nbrDist2","nbrDist2twice",V2_MODIFIERS)
  if(e%in%ignored)parameter<-0L
  atom<-list(effect=e,parameter=parameter)
  if(e%in%V2_MODIFIERS)atom$covariate<-as.character(row$interaction1)
  v2_atom(atom,internal=TRUE)
}
v2_new_allocator <- function(netdata) {
  # Authors' predictive controls and defense-spending objective unchanged.
  eff<-model_effects(netdata,character())
  eff$.spec_key<-v2_native_base_key(eff)
  eff$.spec_role<-ifelse(eff$include,"original_control_or_spending","unused_native_template")
  for(i in seq_len(nrow(eff))) {
    atom<-v2_native_row_atom(eff[i,,drop=FALSE])
    if(!is.null(atom))eff$.spec_key[i]<-paste0("network|",v2_term_key(atom))
  }
  state<-new.env(parent=emptyenv());state$effects<-eff;state$templates<-eff
  state
}
v2_allocate_atom <- function(state,atom) {
  atom<-v2_atom(atom,internal=TRUE);key<-paste0("network|",v2_term_key(atom))
  ix<-which(state$effects$.spec_key==key)
  if(length(ix)>1L)stop("Ambiguous native atom identity: ",key)
  if(length(ix))return(ix)
  t<-state$templates
  ix<-which(t$name=="dv.net"&t$type=="eval"&t$shortName==atom$effect&
            t$interaction1==(atom$covariate%||%"")&t$interaction2=="")
  if(length(ix)!=1L)stop("Native effect template is unsupported/ambiguous: ",key)
  row<-t[ix,,drop=FALSE]
  row$parm<-atom$parameter;row$initialValue<-0;row$include<-FALSE;row$fix<-FALSE
  row$effect1<-0L;row$effect2<-0L;row$effect3<-0L
  row$effectNumber<-max(state$effects$effectNumber)+1L
  row$.spec_key<-key;row$.spec_role<-"native_parameterized_instance"
  # Printed parameter labels must not keep the template's old number.
  row$effectName<-paste0(atom$effect,"[",atom$parameter,"]",if(!is.null(atom$covariate))paste0("(",atom$covariate,")")else"")
  row$functionName<-row$effectName
  rownames(row)<-paste0("v2.",row$effectNumber)
  state$effects<-rbind(state$effects,row)
  nrow(state$effects)
}
v2_allocate_term <- function(state,term,requested=TRUE,role="evolved_network_term") {
  term<-v2_term(term,internal=TRUE)
  key<-paste0("network|",v2_term_key(term))
  ix<-which(state$effects$.spec_key==key)
  if(length(ix)>1L)stop("Ambiguous native term identity: ",key)
  if(!length(ix)) {
    if(is.null(term$product))ix<-v2_allocate_atom(state,term)
    else {
      indices<-vapply(term$product,function(atom)v2_allocate_atom(state,atom),integer(1))
      native_types<-state$effects$interactionType[indices]
      expected_types<-vapply(term$product,v2_interaction_type,character(1))
      if(!identical(as.character(native_types),expected_types))stop("Installed native interaction metadata differs from the pinned catalog")
      t<-state$templates
      base<-which(t$name=="dv.net"&t$type=="eval"&t$shortName=="unspInt")
      if(!length(base))stop("No native unspInt row template")
      row<-t[base[1],,drop=FALSE]
      row$effectNumber<-max(state$effects$effectNumber)+1L
      ids<-c(state$effects$effectNumber[indices],rep(0L,3L-length(indices)))
      row$effect1<-ids[1];row$effect2<-ids[2];row$effect3<-ids[3]
      row$parm<-0L;row$initialValue<-0;row$fix<-FALSE;row$include<-FALSE
      row$.spec_key<-key;row$.spec_role<-role
      row$effectName<-v2_term_key(term);row$functionName<-row$effectName
      rownames(row)<-paste0("v2.",row$effectNumber)
      state$effects<-rbind(state$effects,row);ix<-nrow(state$effects)
    }
  }
  if(requested) {
    state$effects$include[ix]<-TRUE
    if(state$effects$.spec_role[ix]!="original_control_or_spending")state$effects$.spec_role[ix]<-role
  }
  ix
}
build_network_effects_v2 <- function(netdata,spec) {
  catalog<-read_json("configs/effect-catalog-v2.json",simplifyVector=TRUE)
  shape<-dim(netdata$depvars$dv.net)
  if(!identical(as.integer(catalog$network_node_count),V2_NETWORK_NODE_COUNT)||
     length(shape)!=3L||!identical(as.integer(shape[1:2]),rep(V2_NETWORK_NODE_COUNT,2L)))
    stop("Native country count differs from the declared structured catalog; do not change the sample to satisfy truncation bounds")
  spec<-validate_network_specification_v2(spec)
  state<-v2_new_allocator(netdata)
  for(term in spec$network_effects)v2_allocate_term(state,term)
  state$effects<-RSiena:::fixUpEffectNames(state$effects)
  if(anyDuplicated(state$effects$effectNumber)||anyDuplicated(state$effects$.spec_key[state$effects$include]))stop("Nonunique native instance allocation")
  list(effects=state$effects,state=state,specification=spec)
}

v2_legacy_terms <- function(spec) {
  spec<-validate_network_specification_v2(spec)
  parameters<-c(degPlus=1L,transTriads=0L,inPop=0L,gwesp=69L)
  terms<-spec$network_effects
  if(length(terms)>3L||any(vapply(terms,function(term)
    !is.null(term$product)||!is.null(term$covariate)||
    !term$effect%in%names(parameters)||term$parameter!=parameters[[term$effect]],logical(1))))return(NULL)
  sort(vapply(terms,function(term)term$effect,character(1)),method="radix")
}

# Strict provenance identity for importing an unchanged legacy fitted model.
# Unlike native updateTheta this includes the native internal parameter, all
# variable/group/period fields, and recursively resolved operand identities.
# Effect numbers locate operands but do not themselves define model identity.
v2_native_identity <- function(rows,universe=rows) {
  fields<-c("name","type","shortName","interaction1","interaction2","parm",
    "group","groupName","period","netType","rateType","setting",
    "basicRate","fix","test","randomEffects","timeDummy")
  required<-c(fields,"effectNumber","effect1","effect2","effect3")
  if(!is.data.frame(rows)||!is.data.frame(universe)||
     !all(required%in%names(rows))||!all(required%in%names(universe))||
     anyDuplicated(universe$effectNumber))stop("Native effect identity metadata is incomplete or ambiguous")
  resolve<-function(row,visited=integer()) {
    number<-row$effectNumber
    if(length(number)!=1L||is.na(number)||number%in%visited)stop("Malformed/cyclic native interaction operand identity")
    base<-as.list(vapply(fields,function(field)as.character(row[[field]]),character(1)))
    names(base)<-fields
    ids<-as.numeric(unlist(row[c("effect1","effect2","effect3")],use.names=FALSE))
    if(anyNA(ids)||any(ids<0)||any(ids!=floor(ids)))stop("Malformed native operand references")
    ids<-ids[ids>0]
    if(length(ids)) {
      if(!length(ids)%in%c(2L,3L)||!row$shortName%in%c("unspInt","behUnspInt","contUnspInt"))
        stop("Unsupported native interaction identity")
      ix<-match(ids,universe$effectNumber)
      if(anyNA(ix))stop("Saved native interaction operand is missing from the effect universe")
      operands<-lapply(ix,function(i)resolve(universe[i,,drop=FALSE],c(visited,number)))
      base$operands<-unname(operands[order(vapply(operands,v2_json_key,character(1)),method="radix")])
    }
    base
  }
  vapply(seq_len(nrow(rows)),function(i)v2_json_key(resolve(rows[i,,drop=FALSE])),character(1))
}

v2_adopt_legacy_fit <- function(fit,effects,spec,provenancefile=NULL) {
  if(!inherits(fit,"sienaFit")||isTRUE(fit$gmm)||isTRUE(fit$cconditional))
    stop("Imported checkpoint must be an unconditional native Siena fit")
  previous<-fit$requestedEffects
  if(".spec_key"%in%names(previous))return(fit)
  legacy<-v2_legacy_terms(spec)
  if(is.null(legacy))stop("An untagged legacy fit can be reused only for an exactly v1-representable specification")
  if(nrow(previous)!=length(fit$theta)||!".spec_key"%in%names(effects))
    stop("Imported native fit has an invalid coefficient/identity shape")
  wanted<-effects[effects$include,,drop=FALSE]
  # Reproduce native grouping without permuting any row within a dependent
  # variable. A difference in the ordered identity vector fails closed.
  wanted<-do.call(rbind,lapply(unique(previous$name),function(name)wanted[wanted$name==name,,drop=FALSE]))
  universe<-if(is.data.frame(fit$effects))fit$effects else previous
  oldkeys<-v2_native_identity(previous,universe)
  newkeys<-v2_native_identity(wanted,effects)
  if(anyDuplicated(oldkeys)||anyDuplicated(newkeys)||!identical(oldkeys,newkeys))
    stop("Imported legacy fit differs in ordered native effects, parameters or operands; no coefficient/derivative reuse allowed")
  previous$.spec_key<-wanted$.spec_key
  previous$.spec_role<-wanted$.spec_role
  fit$requestedEffects<-previous
  # Only descriptive identity columns are added. In particular theta, sf,
  # dfra, dinv, fixed flags, effect numbers and random state remain untouched.
  report<-list(version="legacy-native-fit-tagging-v1",legacy_network_effects=unname(legacy),
    timestamp_utc=format(Sys.time(),"%Y-%m-%dT%H:%M:%SZ",tz="UTC"),
    exact_ordered_native_identity=TRUE,estimated_parameters=nrow(previous),
    coefficients_reordered=FALSE,derivatives_modified=FALSE,native_parameters_modified=FALSE,
    source_checkpoint_rewritten=FALSE,specification_keys=as.list(previous$.spec_key),
    native_identity=as.list(oldkeys))
  fit$structured_legacy_adoption<-report
  if(!is.null(provenancefile))write_json(report,provenancefile,auto_unbox=TRUE,pretty=TRUE,digits=16)
  fit
}

v2_update_theta <- function(effects,prevAns,varName=NULL) {
  if(!inherits(prevAns,"sienaFit")||isTRUE(prevAns$gmm)||isTRUE(prevAns$cconditional)||!is.null(varName))
    stop("Structured warm start only supports the declared unconditional same-specification SAOM")
  previous<-prevAns$requestedEffects
  if(!".spec_key"%in%names(effects)||!".spec_key"%in%names(previous)||nrow(previous)!=length(prevAns$theta)||
     anyDuplicated(previous$.spec_key)||any(!is.finite(prevAns$theta)))stop("Previous fit lacks complete structured effect identities")
  wanted<-effects[effects$include,,drop=FALSE]
  # Native initializeFRAN groups requested rows by dependent variable before
  # retaining derivative matrices. Confirm exact identity/order, not just size.
  wanted<-do.call(rbind,lapply(unique(previous$name),function(name)wanted[wanted$name==name,,drop=FALSE]))
  if(!identical(as.character(wanted$.spec_key),as.character(previous$.spec_key)))
    stop("Structured warm-start identity/order mismatch; derivative reuse would be unsafe")
  index<-match(effects$.spec_key,previous$.spec_key)
  use<-which(!is.na(index));effects$initialValue[use]<-prevAns$theta[index[use]]
  effects
}

# Focused R adapter correction: private lexical copies of these three native
# functions retain their original bodies and delegate every native operation
# unchanged. Only updateTheta resolves to the full-instance-key helper above.
# No unlockBinding/assignInNamespace, installed-source edit, or C++ change.
v2_native_runner <- function() {
  if(as.character(packageVersion("RSiena"))!="1.3.10")stop("Structured adapter requires pinned RSiena 1.3.10")
  bridge<-new.env(parent=asNamespace("RSiena"))
  bridge$updateTheta<-v2_update_theta
  for(name in c("initializeFRAN","robmon","siena07")) {
    fn<-get(name,envir=asNamespace("RSiena"));environment(fn)<-bridge
    assign(name,fn,envir=bridge)
  }
  bridge$siena07
}

# Cooperative operation boundary only: never interrupt an admitted native fit.
# The reused fit_model writes the previous completed attempt and diagnostics
# before it reaches the next wrapped siena07 entry point.
v2_checkpoint_boundary <- function(outdir,stage,next_attempt=NULL) {
  raw<-Sys.getenv("SHINKA_EXECUTION_DEADLINE",unset="")
  if(!nzchar(raw))return(invisible(TRUE))
  deadline<-suppressWarnings(as.numeric(raw))
  if(length(deadline)!=1L||!is.finite(deadline)||deadline<=0)
    stop("SHINKA_EXECUTION_DEADLINE must contain finite positive Unix seconds")
  now<-as.numeric(Sys.time());paused<-now>=deadline
  checkpoint<-list(status=if(paused)"paused_execution_window"else"operation_admitted",
    stage=stage,next_attempt=next_attempt,
    timestamp_utc=format(as.POSIXct(now,origin="1970-01-01",tz="UTC"),"%Y-%m-%dT%H:%M:%SZ",tz="UTC"),
    deadline_unix=deadline,
    policy="Completed native operations are retained; no new fit, continuation or forecast begins at/after the execution deadline",
    scientific_validity="Execution checkpoint only; no fitness or estimation-loss value assigned")
  path<-file.path(outdir,"checkpoint.json")
  write_json(checkpoint,paste0(path,".pending"),auto_unbox=TRUE,pretty=TRUE,null="null",digits=16)
  if(!file.rename(paste0(path,".pending"),path))stop("Could not publish cooperative execution checkpoint")
  if(paused)quit(save="no",status=75L,runLast=FALSE)
  invisible(TRUE)
}
fit_model_v2 <- function(netdata,effs,settings,outdir,spec) {
  # Reuse the declared estimation schedule, diagnostics, retry policy and
  # atomic checkpoints; substitute only the scoped native entry point.
  native<-v2_native_runner()
  scope<-new.env(parent=environment(fit_model))
  # Read copied legacy checkpoints without overwriting their original bytes.
  # Fresh structured attempts already carry keys and need no adoption.
  scope$readRDS<-function(file,...) {
    value<-base::readRDS(file,...)
    if(inherits(value,"sienaFit"))value<-v2_adopt_legacy_fit(value,effs,spec,
      file.path(outdir,paste0(basename(file),".legacy-tagging.json")))
    value
  }
  scope$siena07<-function(x,...) {
    name<-basename(x$projname)
    if(!grepl("^fit-[0-9]+$",name))stop("Cannot identify the structured native attempt at its execution boundary")
    attempt<-as.integer(sub("^fit-","",name))
    v2_checkpoint_boundary(outdir,if(attempt==1L)"fit"else"fit_continuation",attempt)
    native(x,...)
  }
  run<-fit_model;environment(run)<-scope
  run(netdata,effs,settings,outdir)
}

forward_effects_v2 <- function(forward,train,fit,spec) {
  built<-build_network_effects_v2(forward$netdata,spec);state<-built$state
  fitted<-fit$requestedEffects
  if(!".spec_key"%in%names(fitted)||nrow(fitted)!=length(fit$theta)||
     anyDuplicated(fitted$.spec_key)||any(!is.finite(fit$theta)))stop("Fitted structured identities/coefficients malformed")
  fitted$estimate<-as.numeric(fit$theta);rates<-list()
  for(i in which(state$effects$include)) {
    eff<-state$effects[i,,drop=FALSE]
    if(eff$type=="rate") {
      rows<-which(fitted$name==eff$name&fitted$type=="rate"&fitted$shortName==eff$shortName&is.finite(fitted$estimate))
      if(!length(rows))stop("No estimable training rate for ",eff$name)
      row<-rows[which.max(as.numeric(fitted$period[rows]))]
      value<-fitted$estimate[row]
      if(value<=0)stop("Nonpositive carried training rate")
      state$effects$initialValue[i]<-value
      rates[[eff$name]]<-list(value=value,training_period=fitted$period[row],duration_adjustment=1)
    } else {
      row<-match(eff$.spec_key,fitted$.spec_key)
      if(is.na(row))stop("Missing fitted term identity: ",eff$.spec_key)
      state$effects$initialValue[i]<-fitted$estimate[row]
    }
  }
  delta<-forward$audit$forward_behavior_mean-forward$audit$training_behavior_mean
  adjustments<-list()
  add_coefficient<-function(term,amount,source) {
    ix<-v2_allocate_term(state,term,requested=TRUE,role="fixed_forecast_reparameterization")
    state$effects$initialValue[ix]<-state$effects$initialValue[ix]+amount
    adjustments[[length(adjustments)+1L]]<<-list(source=source,destination=state$effects$.spec_key[ix],coefficient_increment=amount)
  }
  density<-list(effect="density",parameter=0L)
  # Original spending-alter and quadratic-behavior corrections are retained.
  altkey<-paste0("network|",v2_term_key(list(effect="altX",parameter=0L,covariate="milex.beh")))
  alt<-match(altkey,fitted$.spec_key)
  if(is.na(alt))stop("Original spending-alter control missing")
  add_coefficient(density,fitted$estimate[alt]*delta,altkey)
  linear<-which(state$effects$include&state$effects$name=="milex.beh"&state$effects$shortName=="linear")
  quad<-which(state$effects$include&state$effects$name=="milex.beh"&state$effects$shortName=="quad")
  if(length(linear)!=1L||length(quad)!=1L)stop("Original behavior shapes missing")
  amount<-2*state$effects$initialValue[quad]*delta
  state$effects$initialValue[linear]<-state$effects$initialValue[linear]+amount
  adjustments[[length(adjustments)+1L]]<-list(source=state$effects$.spec_key[quad],destination=state$effects$.spec_key[linear],coefficient_increment=amount)
  # Native product contributions multiply two/three factor contributions.
  # For each centered dynamic factor q_train=q_forward+delta, expand every
  # nonempty subset of constants. Repeated factors contribute multiplicities.
  for(term in built$specification$network_effects)if(!is.null(term$product)) {
    atoms<-term$product
    dynamic<-which(vapply(atoms,function(a)a$effect%in%c("egoX","altX")&&identical(a$covariate,"milex.beh"),logical(1)))
    if(!length(dynamic))next
    sourcekey<-paste0("network|",v2_term_key(term));row<-match(sourcekey,fitted$.spec_key)
    if(is.na(row))stop("Missing fitted dynamic-product coefficient: ",sourcekey)
    gamma<-fitted$estimate[row]
    for(mask in seq_len(2^length(dynamic)-1L)) {
      bits<-as.logical(intToBits(mask))[seq_along(dynamic)];removed<-dynamic[bits]
      remaining<-atoms[-removed]
      lower<-if(!length(remaining))density else if(length(remaining)==1L)remaining[[1]] else list(product=remaining)
      add_coefficient(lower,gamma*delta^length(removed),sourcekey)
    }
  }
  state$effects$fix[state$effects$include]<-TRUE
  state$effects<-RSiena:::fixUpEffectNames(state$effects)
  if(any(!is.finite(state$effects$initialValue[state$effects$include])))stop("Nonfinite forward reparameterization")
  list(effects=state$effects,rates=rates,mean_shift=delta,centering_corrections=adjustments)
}
