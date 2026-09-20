# Plot observed estimation diagnostics only; never substitute them for fitness.
suppressPackageStartupMessages({library(jsonlite);library(ggplot2)})
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop("Usage: plot_baseline_convergence.R FIT_DIAGNOSTICS_JSON SETTINGS_JSON OUTPUT_DIR")
diagnostics<-read_json(args[[1]],simplifyVector=TRUE)
settings<-read_json(args[[2]],simplifyVector=TRUE)
out<-args[[3]];dir.create(out,recursive=TRUE,showWarnings=FALSE)
stopifnot(nrow(diagnostics)>0,all(is.finite(diagnostics$maximum_absolute_t_ratio)),
          all(is.finite(diagnostics$overall_maximum_convergence)))
fields<-c(maximum_absolute_t_ratio="A  Maximum absolute convergence t",
          overall_maximum_convergence="B  Overall convergence ratio")
thresholds<-c(maximum_absolute_t_ratio=settings$estimation$max_abs_convergence_t,
              overall_maximum_convergence=settings$estimation$max_overall_convergence)
table<-do.call(rbind,lapply(names(fields),function(field)
    data.frame(attempt=diagnostics$attempt,metric=unname(fields[[field]]),
        value=diagnostics[[field]],threshold=unname(thresholds[[field]]),
        threshold_met=diagnostics[[field]]<thresholds[[field]],
        accepted_fit=diagnostics$valid,elapsed_seconds=diagnostics$elapsed_seconds)))
table$metric<-factor(table$metric,levels=unname(fields))
table$status<-factor(ifelse(table$threshold_met,"Threshold met","Threshold not met"),
                    levels=c("Threshold not met","Threshold met"))
limits<-unique(table[c("metric","threshold")])
limits$label<-sprintf("Required: < %.2f",limits$threshold)
write.csv(table,file.path(out,"baseline_convergence_plot_data.csv"),row.names=FALSE)
plot<-ggplot(table,aes(x=attempt,y=value))+
    geom_rect(data=limits,aes(xmin=-Inf,xmax=Inf,ymin=0,ymax=threshold),
              inherit.aes=FALSE,fill="#EEF5F1")+
    geom_hline(data=limits,aes(yintercept=threshold),color="#64776B",linewidth=.55,linetype="dashed")+
    geom_line(color="#AAB4BD",linewidth=.65)+
    geom_point(aes(fill=status),shape=21,color="white",stroke=.9,size=4.2)+
    geom_text(aes(label=sprintf("%.4f",value)),vjust=-1.2,size=3.5,color="#243342")+
    geom_text(data=limits,aes(x=3.77,y=threshold,label=label),inherit.aes=FALSE,
              hjust=1,vjust=1.6,size=3,color="#516658")+
    facet_wrap(~metric,scales="free_y",nrow=1)+
    scale_x_continuous(breaks=diagnostics$attempt,limits=c(.8,3.85),expand=c(0,0))+
    scale_y_continuous(expand=expansion(mult=c(0,.17)))+
    scale_fill_manual(values=c("Threshold not met"="#B75C37","Threshold met"="#28766B"))+
    labs(title="Empirical baseline: convergence remains unresolved",
         subtitle="Original predictive Model 3 | Training observations: 1990-2005 | Target year: 2006",
         x="Predeclared estimation attempt",y=NULL,fill=NULL,
         caption=paste("Estimation diagnostics only. No forecast PR-AUC or evolutionary fitness is available.",
                       "Acceptance requires both strict thresholds and all native validity checks; none of these three fits was accepted.",sep="\n"))+
    theme_minimal(base_size=11,base_family="sans")+
    theme(plot.title=element_text(size=16,face="bold",color="#1E3448",margin=margin(b=7)),
          plot.subtitle=element_text(size=10.5,color="#586675",margin=margin(b=20)),
          plot.title.position="plot",plot.caption.position="plot",
          plot.caption=element_text(hjust=0,size=8.5,color="#586675",lineheight=1.3,margin=margin(t=16)),
          strip.text=element_text(face="bold",size=10.5,hjust=0,color="#243342",margin=margin(b=12)),
          panel.grid.minor=element_blank(),panel.grid.major.x=element_blank(),
          panel.grid.major.y=element_line(color="#E3E8ED",linewidth=.3),
          panel.spacing=grid::unit(2,"lines"),legend.position="bottom",
          legend.justification="left",legend.text=element_text(size=9),
          axis.title.x=element_text(size=9.5,margin=margin(t=10)),
          axis.text=element_text(color="#586675"),plot.margin=margin(20,20,14,18))
ggsave(file.path(out,"baseline_convergence.pdf"),plot,width=10,height=5,device="pdf")
ggsave(file.path(out,"baseline_convergence.png"),plot,width=10,height=5,dpi=200,bg="white")
write_json(list(kind="estimation diagnostic, not predictive results",target=2006,
    training_years=c(1990,2005),diagnostics_source=normalizePath(args[[1]]),
    diagnostics_md5=unname(tools::md5sum(args[[1]])),settings_md5=unname(tools::md5sum(args[[2]])),
    complete_attempts=nrow(diagnostics),accepted_fits=sum(diagnostics$valid),
    maximum_absolute_t_threshold=thresholds[[1]],overall_convergence_threshold=thresholds[[2]],
    comparison="strictly less than",outputs=c("baseline_convergence.png","baseline_convergence.pdf","baseline_convergence_plot_data.csv")),
    file.path(out,"baseline_convergence_manifest.json"),auto_unbox=TRUE,pretty=TRUE,digits=16)
cat("Saved convergence diagnostic PNG/PDF and underlying data from",nrow(diagnostics),"actual fits.\n")
