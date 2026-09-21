# Focused read-only numerical diagnosis of three existing training fits.
# No fitting, simulation, target outcomes, evaluation policy or saved-fit edits.
source_dir <- "results/cache/ed64802bacb0fbdd1ae1bc45746e29795f85bc0f92ceedf427660ea0c40efc99"
output_dir <- "results/evolution_forecast/diagnosis-2009"
dir.create(output_dir,recursive=TRUE,showWarnings=FALSE)
library(jsonlite)
options(digits=16)
summaries <- list(); compact <- list()
condition <- function(x) {s<-svd(x,nu=0,nv=0)$d;max(s)/min(s)}
frob <- function(x) sqrt(sum(x*x))
for(attempt in 1:3) {
  file<-file.path(source_dir,paste0("fit-attempt-",attempt,".rds"))
  f<-readRDS(file)
  cat("Attempt",attempt,"object bytes",as.numeric(object.size(f)),"\n")
  effects<-f$requestedEffects
  labels<-paste(effects$name,effects$effectName,sep=" :: ")
  ids<-paste(effects$name,effects$type,effects$shortName,effects$interaction1,
    effects$interaction2,effects$parm,effects$period,sep="|")
  use<-which(!f$fixed); sf<-f$sf[,use,drop=FALSE]
  m<-colMeans(sf); V<-f$msf[use,use,drop=FALSE]; sdstat<-sqrt(diag(V))
  C<-V/outer(sdstat,sdstat); z<-m/sdstat
  inverse_z<-solve(C,z); overall<-sqrt(sum(z*inverse_z))
  optimal_weights<-inverse_z/overall
  eig<-eigen(C,symmetric=TRUE); projections<-as.vector(crossprod(eig$vectors,z))
  contributions<-projections^2/eig$values
  # Deterministic dependence sensitivity for Monte Carlo means, using only
  # saved phase3 rows. This is not a resampling run or a significance test.
  centered<-sweep(sweep(sf,2,m,"-"),2,sdstat,"/")
  white<-sweep(centered%*%eig$vectors,2,sqrt(eig$values),"/")
  n<-nrow(sf);p<-ncol(sf)
  trace_acov<-vapply(1:50,function(lag)
    sum(white[seq_len(n-lag),,drop=FALSE]*white[(lag+1L):n,,drop=FALSE])/(n-lag),numeric(1))
  mc_rows<-do.call(rbind,lapply(c(10L,20L,50L),function(bandwidth) {
    longrun_trace<-p+2*sum((1-(1:bandwidth)/(bandwidth+1))*trace_acov[1:bandwidth])
    data.frame(attempt=attempt,bandwidth=bandwidth,
      whitened_longrun_variance_trace=longrun_trace,
      monte_carlo_squared_ratio_scale=longrun_trace/n,
      monte_carlo_ratio_scale=sqrt(longrun_trace/n),
      observed_squared_ratio=overall^2,
      observed_minus_MC_squared_ratio=overall^2-longrun_trace/n)
  }))
  write.csv(mc_rows,file.path(output_dir,paste0("attempt-",attempt,"-MC-dependence-sensitivity.csv")),row.names=FALSE)
  rm(centered,white)
  rank<-order(contributions,decreasing=TRUE)
  J<-f$dfra[use,use,drop=FALSE]
  Jrow<-sweep(J,1,sdstat,"/")
  norms<-sqrt(colSums(Jrow*Jrow)); Junit<-sweep(Jrow,2,norms,"/")
  se<-sqrt(diag(f$covtheta))[use]
  Jse<-sweep(Jrow,2,se,"*")
  sv<-svd(Junit)
  P<-f$covtheta[use,use,drop=FALSE]/outer(se,se)
  peig<-eigen(P,symmetric=TRUE,only.values=TRUE)$values
  nr_step<-as.vector(-solve(J,m))
  lag1<-vapply(seq_len(ncol(sf)),function(i)cor(sf[-nrow(sf),i],sf[-1,i]),numeric(1))
  table<-data.frame(attempt=attempt,index=use,effect=labels[use],identity=ids[use],
    theta=f$theta[use],parameter_se=se,mean_deviation=m,simulation_sd=sdstat,
    convergence_t=z,native_t=f$tconv[use],optimal_standardized_weight=optimal_weights,
    signed_contribution_to_overall=z*optimal_weights,
    reported_standardized_newton_step=nr_step/se,
    phase3_lag1_correlation=lag1)
  write.csv(table,file.path(output_dir,paste0("attempt-",attempt,"-named-moments.csv")),row.names=FALSE)
  eigenrows<-do.call(rbind,lapply(head(rank,5),function(k) {
    load<-eig$vectors[,k];ix<-head(order(abs(load),decreasing=TRUE),8)
    data.frame(attempt=attempt,eigen_index=k,eigenvalue=eig$values[k],
      squared_ratio_contribution=contributions[k],fraction_of_squared_ratio=contributions[k]/overall^2,
      index=use[ix],effect=labels[use[ix]],standardized_eigen_loading=load[ix])
  }))
  write.csv(eigenrows,file.path(output_dir,paste0("attempt-",attempt,"-dominant-moment-directions.csv")),row.names=FALSE)
  weak<-tail(seq_along(sv$d),3)
  weakrows<-do.call(rbind,lapply(weak,function(k) {
    load<-sv$v[,k];ix<-head(order(abs(load),decreasing=TRUE),8)
    data.frame(attempt=attempt,singular_index=k,singular_value=sv$d[k],
      effect=labels[use[ix]],column_normalized_parameter_direction=load[ix])
  }))
  write.csv(weakrows,file.path(output_dir,paste0("attempt-",attempt,"-weak-derivative-directions.csv")),row.names=FALSE)
  groups<-paste(effects$name[use],effects$type[use],sep="/")
  group_rows<-do.call(rbind,lapply(unique(groups),function(group) {
    ix<-which(groups==group);other<-which(groups!=group)
    marginal<-sum(z[ix]*solve(C[ix,ix,drop=FALSE],z[ix]))
    remaining<-if(length(other))sum(z[other]*solve(C[other,other,drop=FALSE],z[other]))else 0
    data.frame(attempt=attempt,group=group,parameters=length(ix),
      marginal_convergence=sqrt(marginal),
      additional_squared_ratio_conditional_on_other_groups=overall^2-remaining)
  }))
  write.csv(group_rows,file.path(output_dir,paste0("attempt-",attempt,"-moment-groups.csv")),row.names=FALSE)
  block_rows<-do.call(rbind,lapply(split(seq_len(nrow(sf)),ceiling(seq_len(nrow(sf))/250)),function(ix) {
    bm<-colMeans(sf[ix,,drop=FALSE])/sdstat
    data.frame(attempt=attempt,first_iteration=min(ix),last_iteration=max(ix),n=length(ix),
      overall_using_full_covariance=sqrt(sum(bm*solve(C,bm))),
      maximum_absolute_t=max(abs(bm)),
      mean_along_full_sample_maximizing_direction=sum(optimal_weights*bm))
  }))
  write.csv(block_rows,file.path(output_dir,paste0("attempt-",attempt,"-phase3-blocks.csv")),row.names=FALSE)
  Jprevious<-f$dfra1[use,use,drop=FALSE]
  previous_scaled<-sweep(sweep(Jprevious,1,sdstat,"/"),2,se,"*")
  derivative_difference<-frob(Jse-previous_scaled)/frob(Jse)
  # Native phase1.r543-580: sum within-period population cross-covariances
  # between statistics and score functions. Reconstruct it from saved arrays,
  # then compare deterministic halves to describe derivative MC uncertainty.
  score_derivative<-function(rows) {
    answer<-matrix(0,length(use),length(use))
    for(period in seq_len(dim(f$ssc)[2])) {
      scores<-f$ssc[rows,period,use,drop=FALSE];dim(scores)<-c(length(rows),length(use))
      stats<-f$sf2[rows,period,use,drop=FALSE];dim(stats)<-c(length(rows),length(use))
      scores<-sweep(scores,2,colMeans(scores),"-")
      stats<-sweep(stats,2,colMeans(stats),"-")
      answer<-answer+crossprod(stats,scores)/length(rows)
    }
    answer
  }
  derivative_MC<-NULL
  if(isTRUE(f$sf2.byIteration)&&!isTRUE(f$FinDiff.method)) {
    raw_rebuilt<-score_derivative(seq_len(n))
    first<-score_derivative(seq_len(n%/%2));second<-score_derivative((n%/%2+1L):n)
    scale_derivative<-function(matrix)sweep(sweep(matrix,1,sdstat,"/"),2,se,"*")
    derivative_MC<-list(raw_reconstruction_max_abs_difference=max(abs(raw_rebuilt-J)),
      standardized_reconstruction_relative_Frobenius_difference=frob(scale_derivative(raw_rebuilt-J))/frob(Jse),
      negative_raw_derivative_diagonal=which(diag(raw_rebuilt)<0),
      first_half_vs_full_standardized_relative_difference=frob(scale_derivative(first)-Jse)/frob(Jse),
      second_half_vs_full_standardized_relative_difference=frob(scale_derivative(second)-Jse)/frob(Jse),
      two_halves_standardized_relative_difference=frob(scale_derivative(first-second))/frob(Jse))
    rm(raw_rebuilt,first,second)
  }
  rate<-effects$type[use]=="rate"
  summary<-list(attempt=attempt,source=file,source_md5=unname(tools::md5sum(file)),
    loaded_object_bytes=as.numeric(object.size(f)),parameters=length(use),phase3_iterations=nrow(sf),
    native_termination=f$termination,native_OK=f$OK,native_error=f$error,
    native_covariance_message=f$errorMessage.cov,native_divergence=f$diver,
    native_fixed=f$fixed,native_newfixed=f$newfixed,
    overall=overall,stored_overall=as.numeric(f$tconv.max),
    maximum_absolute_t=max(abs(z)),maximum_t_reconstruction_error=max(abs(z-f$tconv[use])),
    maximum_covariance_reconstruction_error=max(abs(V-cov(sf))),
    moment_correlation_condition=max(eig$values)/min(eig$values),
    moment_correlation_minimum_eigenvalue=min(eig$values),
    moment_correlation_maximum_eigenvalue=max(eig$values),
    raw_statistic_covariance_condition_not_interpreted=condition(V),
    raw_derivative_condition_not_interpreted=condition(J),
    standardized_derivative_unit_column_condition=condition(Junit),
    derivative_parameter_SE_scaled_condition=condition(Jse),
    standardized_derivative_smallest_singular_value=min(sv$d),
    incoming_phase2_to_final_phase3_SE_scaled_derivative_relative_Frobenius_difference=derivative_difference,
    parameter_correlation_condition=max(peig)/min(peig),parameter_correlation_minimum_eigenvalue=min(peig),
    maximum_absolute_diagnostic_newton_step_in_SE=max(abs(nr_step/se)),
    phase3_lag1_median=median(lag1),phase3_lag1_maximum_absolute=max(abs(lag1)),
    heuristic_exact_root_MC_ratio_scale=sqrt(length(use)/nrow(sf)),
    heuristic_note="sqrt(p/n) is a conditional Monte Carlo scale at an exact moment root, not a convergence threshold or significance test; covariance estimation and dependence can change it",
    rate_maximum_absolute_t=max(abs(z[rate])),objective_maximum_absolute_t=max(abs(z[!rate])),
    dominant_covariance_eigendirection_fraction=max(contributions)/overall^2,
    derivative_Monte_Carlo=derivative_MC,
    monte_carlo_dependence_sensitivity=mc_rows,
    variance_reduction_note="Native sf contains raw simulated-statistic minus observed-statistic totals (phase3.r717-723); dolby adjusts estMeans and other algorithm components but the stored overall convergence formula uses raw sf/msf",
    sf2_by_iteration=f$sf2.byIteration,finite_difference=f$FinDiff.method,
    dimensions=list(ssc=dim(f$ssc),sf2=dim(f$sf2),scores=dim(f$scores)))
  summaries[[attempt]]<-summary
  compact[[attempt]]<-list(z=z,C=C,Junit=Junit,Jrow=Jrow,Jse=Jse,theta=f$theta[use],se=se,ids=ids[use],labels=labels[use])
  cat("p",length(use),"overall",overall,"max_t",max(abs(z)),
    "corr_condition",summary$moment_correlation_condition,
    "derivative_condition",summary$standardized_derivative_unit_column_condition,"\n")
  rm(f,sf,V,J,Jprevious);invisible(gc())
}
comparisons<-list()
for(a in 2:3) {
  x<-compact[[a-1]];y<-compact[[a]]
  if(!identical(x$ids,y$ids))stop("Saved fitted effect identity/order changed")
  # A common positive unit scale, derived from both fits' standard errors,
  # makes consecutive derivative changes interpretable across heterogeneous
  # rate/statistic units. Raw matrix condition numbers are not interpreted.
  comparisons[[a-1]]<-list(previous=a-1,current=a,
    standardized_deviation_cosine=sum(x$z*y$z)/sqrt(sum(x$z*x$z)*sum(y$z*y$z)),
    standardized_deviation_sign_agreement=mean(sign(x$z)==sign(y$z)),
    moment_correlation_relative_Frobenius_difference=frob(y$C-x$C)/frob(y$C),
    standardized_unit_column_derivative_relative_Frobenius_difference=frob(y$Junit-x$Junit)/frob(y$Junit),
    max_parameter_change_in_previous_SE=max(abs((y$theta-x$theta)/x$se)),
    max_parameter_change_in_current_SE=max(abs((y$theta-x$theta)/y$se)))
}
write_json(list(created_utc=format(Sys.time(),"%Y-%m-%dT%H:%M:%SZ",tz="UTC"),
  purpose="Stored 2009 fit diagnosis only: no new estimation, simulation or evaluation policy changes",
  native_formula="sqrt(m' V^-1 m), m=colMeans(sf), V=cov(sf), excluding fixed parameters",
  matrix_scaling=list(moment="C=diag(sd)^-1 V diag(sd)^-1",
    derivative="Jrow=diag(sd)^-1 dfra; Junit rescales each parameter column to Euclidean norm1; Jse measures one fitted-SE changes in parameters",
    optimal_direction="w=C^-1 z/sqrt(z' C^-1 z); w'Cw=1 and w'z equals overall ratio; signed per-coordinate contributions are correlated-direction decompositions, not causal importance"),
  attempts=summaries,comparisons=comparisons),file.path(output_dir,"matrix_diagnosis.json"),
  auto_unbox=TRUE,pretty=TRUE,digits=16,na="null",null="null")
