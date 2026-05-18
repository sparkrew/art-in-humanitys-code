use anyhow::{bail, Context, Result};
use clap::Parser;
use dataset_writer::*;
use dsi_progress_logger::{concurrent_progress_logger, ProgressLog};
use env_logger::Env;
use lazy_static::lazy_static;
#[allow(unused_imports)] // to keep debug!() around
use log::{self, debug, info, warn};
use rand::seq::SliceRandom;
use rayon::prelude::*;
use regex::{Regex, RegexBuilder};
use std::path::PathBuf;
use swh_graph::graph::*;
use swh_graph::labels::EdgeLabel;
use swh_graph::stdlib::*;
use swh_graph::NodeType;

/// Mine the HEAD commit of all origins in the Software Heritage graph, check
/// if it contains a README file at root dir and report its SWHID if so.
/// Intended as first step before a second step that actually collects all
/// identified READMEs in a dataset.
#[derive(Parser, Debug)]
#[command(about, long_about = None)]
struct CliArgs {
    /// Basename of the input Software Heritage graph to load
    #[arg(short, long)]
    graph: PathBuf,

    /// Output directory where to store the mined dataset
    #[arg(short, long)]
    outdir: PathBuf,
}

// Note: in this struct SWHIDs are represented as Strings because we want to
// serialize them as plain strings anyway.
#[derive(Debug, Default)]
struct OriginInfo {
    readme_swhid: String, // SWHID of the readme file
    ori_swhid: String,    // SWHID of the origin
    ori_url: String,      // URL of the origin
}

/// Given a graph and a directory node in it (usually, but not necessarily, the
/// *root* directory of a repository), return the node id of a README file
/// contained in it, if it exists.
fn find_readme<G: SwhFullGraph>(graph: &G, dir_nd: NodeId) -> Result<NodeId> {
    lazy_static! {
        static ref README_PATH_RE: Regex = RegexBuilder::new(r"readme\.(md|txt|rst)")
            .case_insensitive(true)
            .build()
            .unwrap();
    }

    let props = graph.properties();
    let nd_type = props.node_type(dir_nd);
    if nd_type != NodeType::Directory {
        bail!("Type of {dir_nd} should be directory, but is {nd_type} instead");
    }
    for (nd, labels) in graph.labeled_successors(dir_nd) {
        let nd_type = props.node_type(nd);
        if nd_type != NodeType::Content {
            continue;
        }
        for label in labels {
            if let EdgeLabel::DirEntry(dentry) = label {
                let file_name = String::from_utf8(props.label_name(dentry.filename_id()));
                if let Ok(s) = file_name {
                    if README_PATH_RE.is_match(&s) {
                        return Ok(nd);
                    }
                }
            }
        }
    }
    bail!("No README file found for directory {dir_nd}")
}

fn mine_origin<G: SwhFullGraph>(graph: &G, ori_nd: NodeId) -> Result<OriginInfo> {
    let props = graph.properties();
    let ori_swhid = props.swhid(ori_nd).to_string();
    let mut ori_info = OriginInfo {
        ori_swhid: ori_swhid.to_string(),
        ..Default::default()
    };

    let Some(ori_url_bin) = props.message(ori_nd) else {
        bail!("Could not read origin URL for node {ori_nd} (SWHID {ori_swhid})");
    };
    let ori_url = std::str::from_utf8(&ori_url_bin).expect("Cannot decode origin URL");
    debug!("Processing origin {ori_swhid} (URL: {ori_url}) ...");
    ori_info.ori_url = ori_url.to_string();

    let Ok(Some((snp_nd, _ts))) = find_latest_snp(&graph, ori_nd) else {
        bail!("No eligible snapshot found for origin {ori_url}");
    };
    // debug!("Origin {ori_url} has {} as its most recent snapshot", props.swhid(snp_nd));
    let Ok(Some(head_nd)) = find_head_rev(&graph, snp_nd) else {
        bail!(
            "No head commit found for origin {ori_url} in snapshot {}",
            props.swhid(snp_nd)
        );
    };
    // debug!("Origin {ori_url} has {} as its head commit", props.swhid(head_nd));

    let Ok(Some(root_dir_nd)) = find_root_dir(&graph, head_nd) else {
        bail!(
            "Cannot find root directory for origin {ori_url} in commit {}",
            props.swhid(head_nd)
        );
    };
    // debug!("Origin {ori_url} has {} as root directory", props.swhid(root_dir_nd));

    if let Ok(readme_nd) = find_readme(&graph, root_dir_nd) {
        // debug!("Origin {ori_url} has README file {}", props.swhid(readme_nd));
        ori_info.readme_swhid = props.swhid(readme_nd).to_string();
    } else {
        bail!("Cannot find README for origin {ori_url}");
    };

    Ok(ori_info)
}

pub fn main(graph: PathBuf, outdir: PathBuf) -> Result<()> {
    let dataset_writer = ParallelDatasetWriter::<CsvZstTableWriter>::new(outdir)
        .expect("Could not create output directory");

    info!("Loading graph...");
    let graph = load_full::<swh_graph::mph::DynMphf>(graph).context("Cannot load graph")?;
    let props = graph.properties();

    info!("Collecting origins...");
    let mut origins: Vec<usize> = (0..graph.num_nodes())
        .into_par_iter()
        .filter(|&node| props.node_type(node) == NodeType::Origin)
        .collect();
    info!("Collected {len} origins.", len = origins.len());

    info!("Shuffling origins...");
    origins.shuffle(&mut rand::rng());

    let mut pl = concurrent_progress_logger!(
        item_name = "origin",
        display_memory = false,
        expected_updates = Some(origins.len()),
    );
    pl.start("Processing origins...");
    origins.into_par_iter().try_for_each_init(
        || (pl.clone(), dataset_writer.get_thread_writer().unwrap()),
        |(pl, table_writer), ori_nd| -> Result<(), std::io::Error> {
            pl.light_update();
            match mine_origin(&graph, ori_nd) {
                Ok(ori_info) => Ok(table_writer.write_record([
                    &ori_info.readme_swhid,
                    &ori_info.ori_swhid,
                    &ori_info.ori_url,
                ])?),
                Err(error) => {
                    let ori_swhid = props.swhid(ori_nd).to_string();
                    debug!("Cannot mine {ori_swhid}, skipping it (error: {error})");
                    Ok(())
                }
            }
        },
    )?;

    pl.done();
    Ok(())
}

pub fn cli() -> Result<()> {
    let args = CliArgs::parse();
    env_logger::Builder::from_env(Env::default().default_filter_or("info")).init();
    main(args.graph.clone(), args.outdir.clone())
}
