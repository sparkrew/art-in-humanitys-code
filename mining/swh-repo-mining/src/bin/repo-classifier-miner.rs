use anyhow::Result;
use swh_repo_mining::repo_classifier_miner::cli;

pub fn main() -> Result<()> {
    cli()
}
