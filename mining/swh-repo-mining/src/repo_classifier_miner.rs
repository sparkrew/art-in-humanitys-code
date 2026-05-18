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
// use std::collections::VecDeque;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::File;
use std::io::Write;
use std::io::{self, BufRead};
use std::path::PathBuf;
use swh_graph::graph::*;
use swh_graph::labels::EdgeLabel;
use swh_graph::stdlib::*;
use swh_graph::NodeType;

/// Extract from origins in the Software Heritage graph useful information to
/// classify repositories: filesystem structure of HEAD commit, README
/// reference.
#[derive(Parser, Debug)]
#[command(about, long_about = None)]
struct CliArgs {
    /// Basename of the input Software Heritage graph to load
    #[arg(short, long)]
    graph: PathBuf,

    /// If given, textual file listing origins to mine as swh:1:ori:... pseudo-SWHIDs.
    /// If not given, all origins in the graph will be mined.
    #[arg(long)]
    origins: Option<PathBuf>,

    /// Output directory where to store the mined dataset
    #[arg(short, long)]
    outdir: PathBuf,
}

// XXX TODO find a better solution for this, e.g., a limit on the maximum number of FsTree nodes
const ORI_BLOCKLIST: &[&str] = &[
    "swh:1:ori:8c686276921af65d1849aa58b0b819c45182fafc", // https://github.com/pharzan/git-bomb
];

/// Simplified version of [swh_graph::stdlib::FsTree], with only UTF-8
/// decodable files and directories. Submodules are represented as empty
/// directories.
#[derive(Debug, Serialize)]
#[serde(untagged)]
enum SimpleFsTree {
    File,
    Dir(HashMap<String, SimpleFsTree>),
}

impl SimpleFsTree {
    /// Create a [SimpleFsTree] by "simplifying" a [swh_graph::stdlib::FsTree],
    /// i.e., dropping all non-representable stuff and decoding strings.
    fn simplify(fs_tree: &FsTree) -> Self {
        match fs_tree {
            FsTree::Content => SimpleFsTree::File,
            FsTree::Directory(entries) => SimpleFsTree::Dir(HashMap::from_iter(
                entries.iter().filter_map(|(name, (entry, _perm))| {
                    if let Ok(name) = String::from_utf8(name.clone()) {
                        Some((name, SimpleFsTree::simplify(entry)))
                    } else {
                        None // skip non UTF-8 entries
                    }
                }),
            )),
            FsTree::Revision(_node) => SimpleFsTree::Dir(HashMap::new()),
        }
    }
}

// Note: in this struct SWHIDs are represented as Strings because, (1) adding
// Serde serializers for orphan structures is cumbersome; (2) we want to
// serialize them as plain strings anyway.
#[derive(Debug, Default, Serialize)]
struct OriginInfo {
    swhid: String,                 // SWHID of the origin
    url: String,                   // URL of the origin
    readme: Option<String>,        // SWHID of the readme file, if found
    fs_tree: Option<SimpleFsTree>, // filesystem tree of the root directory
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

fn mine_origin<G: SwhFullGraph>(graph: &G, ori_nd: usize) -> Result<OriginInfo> {
    let props = graph.properties();
    let ori_swhid = props.swhid(ori_nd).to_string();
    let mut ori_info = OriginInfo {
        swhid: ori_swhid.to_string(),
        ..Default::default()
    };

    let Some(ori_url_bin) = props.message(ori_nd) else {
        bail!("Could not read origin URL for node {ori_nd} (SWHID {ori_swhid})");
    };
    let ori_url = std::str::from_utf8(&ori_url_bin).expect("Cannot decode origin URL");
    debug!("Processing origin {ori_swhid} (URL: {ori_url}) ...");
    ori_info.url = ori_url.to_string();
    if ORI_BLOCKLIST.contains(&ori_swhid.as_str()) {
        bail!("Origin {ori_swhid} is in the blocklist");
    }

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
        ori_info.readme = Some(props.swhid(readme_nd).to_string());
    };

    if let Ok(fs_tree) = fs_ls_tree(&graph, root_dir_nd) {
        // debug!("Origin {ori_url} has filesystem tree: {:?}", fs_tree);
        ori_info.fs_tree = Some(SimpleFsTree::simplify(&fs_tree))
    }

    Ok(ori_info)
}

fn collect_origins<G: SwhFullGraph>(graph: &G, origins_path: Option<PathBuf>) -> Vec<usize> {
    let props = graph.properties();
    if let Some(origins_path) = origins_path {
        // collect only selected origins, skip unresolvable ones
        io::BufReader::new(File::open(origins_path).unwrap())
            .lines()
            .filter_map(|ori_swhid| props.node_id_from_string_swhid(ori_swhid.unwrap()).ok())
            .collect()
    } else {
        // collect all origins in the graph
        (0..graph.num_nodes())
            .filter(|&node| props.node_type(node) == NodeType::Origin)
            .collect()
    }
}

pub fn main(graph: PathBuf, origins: Option<PathBuf>, outdir: PathBuf) -> Result<()> {
    let dataset_writer = ParallelDatasetWriter::<PlainZstTableWriter>::new(outdir)
        .expect("Could not create output directory");

    info!("Loading graph...");
    let graph = load_full::<swh_graph::mph::DynMphf>(graph).context("Cannot load graph")?;

    info!("Collecting origins...");
    let mut origins = collect_origins(&graph, origins);
    info!("Collected {len} origins.", len = origins.len());
    info!("Shuffling origins...");
    origins.shuffle(&mut rand::rng());

    let mut pl = concurrent_progress_logger!(
        item_name = "origin",
        display_memory = false,
        expected_updates = Some(origins.len()),
    );
    pl.threshold(1000);
    pl.start("Processing origins...");
    origins.into_par_iter().try_for_each_init(
        || (pl.clone(), dataset_writer.get_thread_writer().unwrap()),
        |(pl, table_writer), ori_swhid| -> Result<(), std::io::Error> {
            pl.light_update();
            match mine_origin(&graph, ori_swhid) {
                Ok(ori_info) => {
                    table_writer.write_all(&serde_json::to_vec(&ori_info).unwrap())?;
                    table_writer.write_all(b"\n")
                }
                Err(error) => {
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
    main(
        args.graph.clone(),
        args.origins.clone(),
        args.outdir.clone(),
    )
}
