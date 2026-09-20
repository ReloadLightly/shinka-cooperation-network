# Trusted scorer. This is the only forecasting stage that opens target outcomes.
# No candidate source is loaded or executed here.
suppressPackageStartupMessages(library(PRROC))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("PRROC")) == "1.3.1")

curve_metrics <- function(p, y) {
    stopifnot(length(p) == length(y), all(is.finite(p)),
              all(p >= 0 & p <= 1), all(y %in% c(0, 1)))
    both <- length(unique(y)) == 2L
    list(n=length(y), positives=sum(y == 1), negatives=sum(y == 0),
         pr_auc=if (both) PRROC::pr.curve(scores.class0=p[y == 1],
                      scores.class1=p[y == 0], curve=FALSE)$auc.integral else NULL,
         roc_auc=if (both) PRROC::roc.curve(scores.class0=p[y == 1],
                      scores.class1=p[y == 0], curve=FALSE)$auc else NULL,
         brier=if (length(y)) mean((p-y)^2) else NULL,
         limitation=if (!both) "AUC unavailable: subset lacks both outcome classes" else NULL)
}

network_predictive_checks <- function(simulation_path, eligible, observed, expected_count) {
    if(!file.exists(simulation_path)) stop("Native simulations missing for structural predictive checks")
    sims <- readRDS(simulation_path)$sims
    stopifnot(length(sims)==expected_count)
    mask <- eligible | t(eligible)
    summarize <- function(a) {
        a[!mask] <- 0
        graph <- igraph::graph_from_adjacency_matrix(a,mode="undirected",diag=FALSE)
        c(ties=sum(a[eligible]), triangles=sum(igraph::count_triangles(graph))/3,
          clustering=igraph::transitivity(graph,type="globalundirected"),
          degree_variance=var(rowSums(a)))
    }
    empirical <- summarize(observed)
    draws <- vapply(sims,function(sim) {
        edges <- sim[[1]][["dv.net"]][[1]]
        a <- matrix(0,nrow(observed),nrow(observed))
        if(length(edges)) a[edges[,1:2,drop=FALSE]] <- edges[,3]
        stopifnot(all(a %in% c(0,1)),isSymmetric(a))
        summarize(a)
    },numeric(4))
    list(scope="Network restricted to the common eligible dyad mask; inactive and invalid edges absent in both observed and simulated graphs",
         interpretation="Descriptive predictive envelopes, not independent-dyad significance tests or coefficient uncertainty",
         observed=as.list(empirical), simulated=lapply(seq_along(empirical),function(i)
             list(statistic=names(empirical)[i], finite_simulations=sum(is.finite(draws[i,])),
                  mean=if(any(is.finite(draws[i,]))) mean(draws[i,],na.rm=TRUE) else NULL,
                  quantiles_025_50_975=if(any(is.finite(draws[i,]))) unname(quantile(draws[i,],c(.025,.5,.975),na.rm=TRUE)) else NULL)))
}

score_forecast <- function(prediction_path, target_path, output_dir) {
    # A separate process opens these files only after prediction is durably saved.
    pred <- readRDS(prediction_path)
    truth <- readRDS(target_path)
    required <- c("nms", "probabilities", "behavior_mean", "origin_network",
                  "origin_behavior", "origin_active", "target", "simulations", "seed",
                  "forecast_schema_version", "native_origin_active")
    stopifnot(all(required %in% names(pred)), pred$simulations == 1000L,
              identical(pred$forecast_schema_version,"training-only-v2-fixed-origin-membership"),
              identical(as.logical(pred$native_origin_active),as.logical(pred$origin_active)))
    ids <- as.character(pred$nms)
    n <- length(ids)
    stopifnot(!anyDuplicated(ids), identical(dim(pred$probabilities), c(n,n)),
              identical(dim(pred$origin_network), c(n,n)),
              length(pred$origin_active) == n,
              isTRUE(all.equal(pred$probabilities, t(pred$probabilities))),
              all(is.finite(pred$probabilities)),
              all(pred$probabilities >= 0 & pred$probabilities <= 1),
              max(abs(pred$probabilities*pred$simulations-round(pred$probabilities*pred$simulations))) < 1e-8,
              all(diag(pred$probabilities) == 0),
              length(pred$behavior_mean) == n,
              all(is.finite(pred$behavior_mean)),
              all(pred$behavior_mean >= 1 & pred$behavior_mean <= 11),
              max(abs(pred$behavior_mean*pred$simulations-round(pred$behavior_mean*pred$simulations))) < 1e-8,
              length(pred$origin_behavior) == n)
    target_ids <- as.character(truth$nms)
    stopifnot(pred$target == truth$target, !anyDuplicated(target_ids),
              length(truth$present) == length(target_ids),
              identical(dim(truth$network),c(length(target_ids),length(target_ids))),
              isTRUE(all.equal(truth$network,t(truth$network))),
              length(truth$behavior) == length(target_ids))
    ix <- match(ids, target_ids)
    present <- !is.na(ix)
    present[present] <- as.logical(truth$present[ix[present]])
    y <- matrix(NA_real_, n, n)
    behavior <- rep(NA_real_, n)
    available <- which(!is.na(ix))
    y[available, available] <- truth$network[ix[available],ix[available]]
    behavior[available] <- truth$behavior[ix[available]]
    upper <- upper.tri(y)
    origin_active <- as.logical(pred$origin_active)
    stopifnot(!anyNA(origin_active), !anyNA(present),
              all(pred$probabilities[!origin_active,,drop=FALSE]==0),
              all(pred$probabilities[,!origin_active,drop=FALSE]==0))
    active_pairs <- outer(origin_active & present, origin_active & present, "&")
    valid_target <- is.finite(y) & (y == 0 | y == 1)
    valid_origin <- is.finite(pred$origin_network) &
                    (pred$origin_network == 0 | pred$origin_network == 1)
    eligible <- upper & active_pairs & valid_target & valid_origin
    p <- pred$probabilities[eligible]
    labels <- y[eligible]
    origin <- pred$origin_network[eligible]
    primary <- curve_metrics(p, labels)
    if (is.null(primary$pr_auc) || !is.finite(primary$pr_auc))
        stop("Target does not have two eligible outcome classes; no valid fitness.")
    formation <- origin == 0
    dissolution <- origin == 1
    bmask <- origin_active & present & is.finite(behavior) & is.finite(pred$behavior_mean)
    stopifnot(all(behavior[bmask] %in% 1:11),
              all(pred$behavior_mean[bmask] >= 1 & pred$behavior_mean[bmask] <= 11))
    # These descriptive summaries use the same eligible observed dyad set.
    netdiag <- list(expected_ties=sum(p), observed_ties=sum(labels),
                    expected_density=mean(p), observed_density=mean(labels),
                    degree_rmse=sqrt(mean((rowSums(replace(pred$probabilities,
                        !(eligible | t(eligible)), 0))-rowSums(replace(y,
                        !(eligible | t(eligible)), 0)))^2)))
    predictive_checks <- network_predictive_checks(file.path(dirname(prediction_path),"simulations.rds"),
                                                   eligible,y,pred$simulations)
    scored <- list(target=pred$target, simulations=pred$simulations, seed=pred$seed,
                   primary=primary, formation=curve_metrics(p[formation], labels[formation]),
                   dissolution=curve_metrics(1-p[dissolution], 1-labels[dissolution]),
                   persistence=curve_metrics(origin, labels),
                   spending=list(n=sum(bmask), units="ordinal categories 1-11",
                       rmse=if (any(bmask)) sqrt(mean((pred$behavior_mean[bmask]-behavior[bmask])^2)) else NULL),
                   network_diagnostics=netdiag,
                   structural_predictive_checks=predictive_checks,
                   eligibility=list(total_unordered_pairs=sum(upper), eligible=sum(eligible),
                       excluded_inactive=sum(upper & !active_pairs),
                       excluded_target_missing_or_structural=sum(upper & active_pairs & !valid_target),
                       excluded_origin_missing_or_structural=sum(upper & active_pairs & valid_target & !valid_origin),
                       origin_actors=sum(origin_active), target_present_in_sample=sum(present),
                       entered_since_origin_in_training_sample=ids[present & !origin_active],
                       left_since_origin_in_training_sample=ids[!present & origin_active],
                       target_actors_outside_training_sample=setdiff(target_ids[truth$present], ids)))
    dir.create(output_dir, recursive=TRUE, showWarnings=FALSE)
    pairs <- which(upper, arr.ind=TRUE)
    write.csv(data.frame(ccode1=ids[pairs[,1]], ccode2=ids[pairs[,2]],
                         eligible=eligible[upper], origin=pred$origin_network[upper],
                         label=y[upper], probability=pred$probabilities[upper]),
               file.path(output_dir,"eligibility_and_scores.csv"), row.names=FALSE)
    saveRDS(eligible, file.path(output_dir,"eligibility_mask.rds"))
    write_json(scored, file.path(output_dir,"scores.json"), pretty=TRUE, auto_unbox=TRUE,
               digits=16, null="null", na="null")
    scored
}

if (sys.nframe() == 0L) {
    args <- commandArgs(trailingOnly=TRUE)
    if (length(args) != 3L) stop("Usage: R/score.R predictions.rds target.rds output_dir")
    score_forecast(args[[1]], args[[2]], args[[3]])
}
