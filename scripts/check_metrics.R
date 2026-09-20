source("R/score.R")

# Positive/negative argument semantics, tied scores, and probability-first
# aggregation. This tests the estimand, not a reimplementation of PRROC.
stopifnot(abs(curve_metrics(c(.9,.8,.2,.1), c(1,1,0,0))$pr_auc-1) < 1e-12)
stopifnot(abs(curve_metrics(rep(.5,4), c(1,1,0,0))$pr_auc-.5) < 1e-12)
stopifnot(is.null(curve_metrics(c(.2,.3),c(0,0))$pr_auc))
endpoints <- rbind(c(1,0,1,0), c(1,1,0,0), c(0,1,0,1))
y <- c(1,1,0,0)
correct <- curve_metrics(colMeans(endpoints), y)$pr_auc
incorrect <- mean(apply(endpoints, 1, function(x) curve_metrics(x,y)$pr_auc))
stopifnot(abs(correct-incorrect) > 1e-3)
fixture <- list(PRROC=as.character(packageVersion("PRROC")),
                probability_first=correct, mean_hard_network_auc=incorrect,
                tied_scores_auc=.5, positive_class_semantics="scores.class0",
                status="passed")
dir.create("results/verification", recursive=TRUE, showWarnings=FALSE)
jsonlite::write_json(fixture,"results/verification/metric_checks.json",pretty=TRUE,
                     auto_unbox=TRUE,digits=16)
print(fixture)
