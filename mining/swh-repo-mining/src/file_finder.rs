use anyhow::{bail, Context, Result};
use clap::{Parser, ValueEnum};
use dataset_writer::*;
use dsi_progress_logger::{concurrent_progress_logger, ProgressLog};
use env_logger::Env;
use log::{self, debug, info};
use rayon::prelude::*;
use regex::{Regex, RegexBuilder};
use serde::Serialize;
use std::collections::{HashSet, VecDeque};
use std::io::Write;
use std::path::PathBuf;
use swh_graph::graph::*;
use swh_graph::labels::{EdgeLabel, FilenameId};
use swh_graph::stdlib::*;
use swh_graph::utils::shuffle::par_iter_shuffled_range;
use swh_graph::{NodeType, SWHID};

/// Find directory entries with names matching a given regular expression in the entire Software
/// Heritage graph.
#[derive(Parser, Debug)]
#[command(about, long_about = None)]
pub struct CliArgs {
    /// Search mode.
    #[arg(long = "by", value_enum, default_value_t = SearchBy::Origin)]
    pub mode: SearchBy,

    /// Basename of the input Software Heritage graph to load.
    #[arg(short, long, name = "BASENAME")]
    pub graph: PathBuf,

    /// Regular expression of directory entries to find (matching on relative file names,
    /// not full path). Example: '^README\..*'.
    #[arg(short = 'p', long = "pattern")]
    pub regex: String,

    /// Ignore case distinctions in pattern and entry names. Default: false.
    #[arg(short, long, default_value_t = false)]
    pub ignore_case: bool,

    /// Recursively search for matches, stopping after traversing the given maximum number of
    /// directory nodes (in BFS order). Pass 0 or 1 to disable recursion, N>1 to enable it.
    #[arg(short = 'r', long = "recursive", default_value_t = 0, name = "DIRS")]
    pub rec_dirs: usize,

    /// Include in the output the SWHIDs of matching entries. Default: false in origin mode; always
    /// true in directory mode.
    #[arg(short = 's', long, default_value_t = false)]
    pub with_swhids: bool,

    /// Include in the output the name of matching entries. Default: false.
    #[arg(short = 'n', long, default_value_t = false)]
    pub with_filenames: bool,

    /// Only process the given number of origins or directories.
    #[arg(long = "limit")]
    pub limit: Option<usize>,

    /// Output directory where to store results, as sharded NDJSON files. Will be created
    /// if needed.
    #[arg(short, long, name = "DIR")]
    pub outdir: PathBuf,
}

#[derive(Copy, Clone, Debug, Eq, Ord, PartialEq, PartialOrd, ValueEnum)]
pub enum SearchBy {
    /// Iterate through all origins first, then search through their files.
    Origin,

    /// Iterate through all directories, no matter their origins. Note that directory mode tend to
    /// produces many duplicates (one for each *different* directory where a match is found);
    /// deduplication is left as an exercise to the user.
    Directory,
}

/// Criteria used to identify matching directory entries.
pub enum FilenameCrit<'a> {
    /// Entry matches if its [FilenameId] is included in the given set.
    Ids(&'a HashSet<u64>),

    /// Entry matches if its name matches the given [regular expression](Regex).
    Re(&'a Regex),
}

/// Information about one single match, as a (SWHID, filename) pair. Each string of the pair can be
/// None, if the information was not mined.
type MatchInfo = (Option<SWHID>, Option<String>);

/// Information about multiple matches.
type MatchesInfo = Vec<MatchInfo>;

/// Information about an origin with matching directory entries.
#[derive(Debug, Serialize)]
struct OriginMatch {
    /// SWHID of the origin.
    ori_swhid: SWHID,

    /// URL of the origin.
    ori_url: String,

    /// SWHID of the HEAD revision (or release) of origin that was mined.
    head: SWHID,

    /// Total number of matches in the origin.
    match_count: usize,

    /// Information about matching entries. None if no additional information about
    /// matches were mined (to avoid a useless vector of None pairs).
    matches_info: Option<MatchesInfo>,
}

/// Initialize a progress logger for specific items, with common settings.
fn init_progress_logger(
    item_name: &str,
    items_count: usize,
) -> dsi_progress_logger::ConcurrentWrapper {
    let mut pl = concurrent_progress_logger!(
        item_name = item_name,
        display_memory = false,
        expected_updates = Some(items_count),
    );
    pl.threshold(1000);
    pl
}

/// Given a graph and a directory node in it (usually, but not necessarily, the *root* directory of
/// a repository), return information about matching entries contained in it.
pub fn find_files_in_dir<G: SwhFullGraph>(
    graph: &G,
    dir_nd: NodeId,
    crit: &FilenameCrit,
    rec_dirs: usize,
    with_swhids: bool,
    with_filenames: bool,
) -> Result<MatchesInfo> {
    let props = graph.properties();
    assert!(props.node_type(dir_nd) == NodeType::Directory);

    let mut dirs_limit = std::cmp::max(rec_dirs, 1); // bump up to 1 if needed
    let mut dirs_backlog = VecDeque::new();
    dirs_backlog.push_back(dir_nd);
    dirs_limit -= 1; // Invariant: we decrease the limit at every backlog increase. When limit == 0,
                     // we stop adding new dirs to the backlog.

    let mut matches: MatchesInfo = Vec::new(); // Accumulate all matches, including recursive ones
    while let Some(dir_nd) = dirs_backlog.pop_front() {
        for (nd, labels) in graph.labeled_successors(dir_nd) {
            if props.node_type(nd) == NodeType::Directory && dirs_limit > 0 {
                dirs_backlog.push_back(nd);
                dirs_limit -= 1;
            }
            for label in labels {
                if let EdgeLabel::DirEntry(dentry) = label {
                    let mut swhid = None;
                    let mut filename = None;
                    match crit {
                        FilenameCrit::Ids(filename_ids) => {
                            let filename_id = dentry.filename_id();
                            if filename_ids.contains(&filename_id.0) {
                                if with_swhids {
                                    swhid = Some(props.swhid(nd))
                                };
                                if with_filenames {
                                    filename = String::from_utf8(props.label_name(filename_id)).ok()
                                };
                                matches.push((swhid, filename));
                            }
                        }
                        FilenameCrit::Re(filename_re) => {
                            let s = String::from_utf8(props.label_name(dentry.filename_id()));
                            if let Ok(s) = s {
                                if filename_re.is_match(&s) {
                                    if with_swhids {
                                        swhid = Some(props.swhid(nd))
                                    };
                                    if with_filenames {
                                        filename = Some(s);
                                    }
                                    matches.push((swhid, filename));
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if matches.is_empty() {
        bail!("No matches for directory {dir_nd}");
    } else {
        Ok(matches)
    }
}

/// Mine an origin for matching entries. Return success with origin information (about all matches)
/// if at least one match is found.
fn mine_origin<G: SwhFullGraph>(
    graph: &G,
    ori_nd: NodeId,
    filename_re: &Regex,
    rec_dirs: usize,
    with_swhids: bool,
    with_filenames: bool,
) -> Result<OriginMatch> {
    let props = graph.properties();
    let ori_swhid = props.swhid(ori_nd);

    let Some(ori_url_bin) = props.message(ori_nd) else {
        bail!("Could not read origin URL for node {ori_nd} (SWHID {ori_swhid})");
    };
    let ori_url = std::str::from_utf8(&ori_url_bin).expect("Cannot decode origin URL");
    debug!("Processing origin {ori_swhid} (URL: {ori_url}) ...");

    let Ok(Some((snp_nd, _ts))) = find_latest_snp(&graph, ori_nd) else {
        bail!("No eligible snapshot found for origin {ori_url}");
    };
    let Ok(Some(head_nd)) = find_head_rev(&graph, snp_nd) else {
        bail!(
            "No head commit found for origin {ori_url} in snapshot {}",
            props.swhid(snp_nd)
        );
    };
    let Ok(Some(root_dir_nd)) = find_root_dir(&graph, head_nd) else {
        bail!(
            "No root directory found for origin {ori_url} in commit {}",
            props.swhid(head_nd)
        );
    };

    let mut ori_info = OriginMatch {
        ori_swhid,
        ori_url: ori_url.to_string(),
        head: props.swhid(head_nd),
        match_count: 0,
        matches_info: None,
    };
    if let Ok(matches) = find_files_in_dir(
        graph,
        root_dir_nd,
        &FilenameCrit::Re(filename_re),
        rec_dirs,
        with_swhids,
        with_filenames,
    ) {
        if matches.is_empty() {
            bail!("No matches for origin {ori_url}");
        } else {
            ori_info.match_count = matches.len();
            ori_info.matches_info = if !with_swhids && !with_filenames {
                // Avoid serializing a useless vector of (None, None) pairs.
                None
            } else {
                Some(matches)
            }
        }
    } else {
        bail!("No matches for origin {ori_url}");
    };
    Ok(ori_info)
}

/// Select mining roots, i.e., nodes of a given type, limited as needed.
fn select_roots<'g, G: SwhFullGraph + Sync>(
    graph: &'g G,
    node_type: NodeType,
    label: (&str, &str), // (singular, plural)
    limit: Option<usize>,
) -> (
    impl ParallelIterator<Item = <core::ops::Range<usize> as IntoParallelIterator>::Item> + use<'g, G>,
    dsi_progress_logger::ConcurrentWrapper,
) {
    info!("Counting {}...", label.1);
    let count = (0..graph.num_nodes())
        .into_par_iter()
        .filter(|&node| graph.properties().node_type(node) == node_type)
        .count();
    info!("Found {count} {}.", label.1);

    let (limit, updates) = if let Some(lim) = limit {
        let lim = std::cmp::min(lim, count); // clamp to population size
        info!("Limiting processing to the first {lim} {}.", label.1);
        (lim, lim)
    } else {
        (usize::MAX, count)
    };

    let mut pl = init_progress_logger(label.0, updates);
    pl.start(format!("Processing {}...", label.1));
    let it = par_iter_shuffled_range(0..graph.num_nodes())
        .filter(move |&node| graph.properties().node_type(node) == node_type)
        .take_any(limit);
    (it, pl)
}

/// Main loop searching files by origin.
#[allow(clippy::too_many_arguments)]
pub fn find_by_origin(
    graph: PathBuf,
    filename_re: &Regex,
    rec_dirs: usize,
    with_swhids: bool,
    with_filenames: bool,
    limit: Option<usize>,
    outdir: PathBuf,
) -> Result<()> {
    info!("Loading graph...");
    let graph = load_full::<swh_graph::mph::DynMphf>(graph).context("Cannot load graph")?;
    let props = graph.properties();
    let dataset_writer = ParallelDatasetWriter::<PlainZstTableWriter>::new(outdir)
        .expect("Could not create output directory");

    let (origins, mut pl) = select_roots(&graph, NodeType::Origin, ("origin", "origins"), limit);
    origins.try_for_each_init(
        || (pl.clone(), dataset_writer.get_thread_writer().unwrap()),
        |(pl, table_writer), ori_nd| -> Result<(), std::io::Error> {
            pl.light_update();
            match mine_origin(
                &graph,
                ori_nd,
                filename_re,
                rec_dirs,
                with_swhids,
                with_filenames,
            ) {
                Ok(ori_info) => {
                    table_writer.write_all(&serde_json::to_vec(&ori_info).unwrap())?;
                    table_writer.write_all(b"\n")
                }
                Err(error) => {
                    debug!(
                        "Cannot mine {}, skipping it (error: {error})",
                        props.swhid(ori_nd)
                    );
                    Ok(())
                }
            }
        },
    )?;
    pl.done();
    Ok(())
}

// XXX TODO switch to swh-graph proper way of doing this, when available.
// https://gitlab.softwareheritage.org/swh/devel/swh-graph/-/issues/4861
/// Read and return the total number of labels in the graph.
fn labels_count<G: SwhGraph>(graph: &G) -> Result<u64> {
    let path = graph.path().with_extension("labels.count.txt");
    let num_labels: u64 = std::fs::read_to_string(&path)
        .with_context(|| format!("Could not read {}", path.display()))?
        .trim()
        .parse()
        .with_context(|| format!("Could not parse {}'s content as integer", path.display()))?;
    Ok(num_labels)
}

/// Main loop searching files by directory.
pub fn find_by_directory(
    graph: PathBuf,
    filename_re: &Regex,
    with_filenames: bool,
    limit: Option<usize>,
    outdir: PathBuf,
) -> Result<()> {
    info!("Loading graph...");
    let graph = load_full::<swh_graph::mph::DynMphf>(graph).context("Cannot load graph")?;
    let props = graph.properties();

    let dataset_writer = ParallelDatasetWriter::<PlainZstTableWriter>::new(outdir.clone())
        .expect("Could not create output directory");

    let labels_count = labels_count(&graph)?;
    let mut pl = init_progress_logger("label", labels_count as usize);
    pl.start("Filter graph labels for matching file names...");
    let filename_ids: HashSet<u64> = (0..labels_count)
        .into_par_iter()
        .map_init(
            || pl.clone(),
            |pl, label_id| {
                pl.light_update();
                let file_name = String::from_utf8(props.label_name(FilenameId(label_id)));
                if let Ok(file_name) = file_name {
                    if filename_re.is_match(&file_name) {
                        return Some(label_id);
                    }
                }
                None
            },
        )
        .filter_map(|id| id)
        .collect();
    info!("Retained {} matching labels.", filename_ids.len());
    pl.done();

    let (dirs, mut pl) = select_roots(
        &graph,
        NodeType::Directory,
        ("directory", "directories"),
        limit,
    );
    dirs.try_for_each_init(
        || (pl.clone(), dataset_writer.get_thread_writer().unwrap()),
        |(pl, table_writer), dir_nd| -> Result<(), std::io::Error> {
            pl.light_update();
            match find_files_in_dir(
                &graph,
                dir_nd,
                &FilenameCrit::Ids(&filename_ids),
                0,
                true,
                with_filenames,
            ) {
                Ok(matches) => {
                    // flatten nested matches
                    matches.iter().try_for_each(|m| {
                        table_writer.write_all(&serde_json::to_vec(&m).unwrap())?;
                        table_writer.write_all(b"\n")
                    })
                }
                Err(error) => {
                    debug!(
                        "Cannot mine {}, skipping it (error: {error})",
                        props.swhid(dir_nd)
                    );
                    Ok(())
                }
            }
        },
    )?;
    pl.done();
    info!("Tip: to deduplicate results (if desired) use something like: ");
    info!(
        "$ zstdcat {} | sort -u -S 16G | zstdmt - > {}",
        outdir.join("*.zst").display(),
        outdir.join("all.zst").display()
    );
    Ok(())
}

/// Main loop dispatcher.
pub fn main(args: &CliArgs) -> Result<()> {
    let filename_re = RegexBuilder::new(&args.regex)
        .case_insensitive(args.ignore_case)
        .build()
        .unwrap();

    match args.mode {
        SearchBy::Origin => find_by_origin(
            args.graph.clone(),
            &filename_re,
            args.rec_dirs,
            args.with_swhids,
            args.with_filenames,
            args.limit,
            args.outdir.clone(),
        ),
        SearchBy::Directory => find_by_directory(
            args.graph.clone(),
            &filename_re,
            args.with_filenames,
            args.limit,
            args.outdir.clone(),
        ),
    }
}

/// Command-line interface.
pub fn cli() -> Result<()> {
    let args = CliArgs::parse();
    env_logger::Builder::from_env(Env::default().default_filter_or("info")).init();
    main(&args)
}
