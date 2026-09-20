# Plot completed original equilibrium cells, explicitly a partial reproduction.
suppressPackageStartupMessages({library(jsonlite);library(ggplot2)})
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=1L)stop("Usage: plot_equilibrium_partial.R RUN_DIR")
out<-normalizePath(args[[1]])
summary<-read_json(file.path(out,"endpoint_summary.json"),simplifyVector=TRUE)
fields<-c(mean_spending_category="Defense effort (ordinal categories)",density="Network density",
          clustering="Global clustering",centralization="Eigenvector centralization")
rows<-list()
for(name in names(summary$results)) {
    item<-summary$results[[name]];spec<-summary$specifications[[name]]
    rates<-unique(as.numeric(spec$native_theta[spec$effects$type=="rate"]))
    stopifnot(length(rates)==1L,length(spec$native_theta)==nrow(spec$effects),item$simulations==10L)
    for(field in names(fields)) {
        values<-item[[field]]
        rows[[length(rows)+1L]]<-data.frame(rate=rates,metric=unname(fields[[field]]),
            mean=values$mean,lower=values$ci99[1],upper=values$ci99[2],simulations=item$simulations)
    }
}
table<-do.call(rbind,rows)
write.csv(table,file.path(out,"partial_equilibrium_plot_data.csv"),row.names=FALSE)
plot<-ggplot(table,aes(x=rate,y=mean))+geom_line(color="#236680",linewidth=.5)+
    geom_errorbar(aes(ymin=lower,ymax=upper),width=.7,color="#236680")+
    geom_point(size=2,color="#123949")+facet_wrap(~metric,scales="free_y",ncol=2)+
    scale_x_continuous(breaks=sort(unique(table$rate)))+
    labs(title="Original equilibrium diagnostic: completed cells only",
         subtitle=sprintf("Partial coverage: %d of 101 rate settings; 159 countries; 10 native RSiena endpoints per setting",length(unique(table$rate))),
         x="Network and behavior opportunity rates",y=NULL,
         caption="Bars: 99% simulation-mean intervals. This partial grid does not establish equilibrium or reproduce the full published figure.")+
    theme_bw(base_size=10)+theme(panel.grid.minor=element_blank(),plot.caption=element_text(hjust=0,size=8))
ggsave(file.path(out,"partial_equilibrium.pdf"),plot,width=10,height=6,device="pdf")
ggsave(file.path(out,"partial_equilibrium.png"),plot,width=10,height=6,dpi=160)
cat("Saved explicitly partial equilibrium diagnostic figure and plot data.\n")
