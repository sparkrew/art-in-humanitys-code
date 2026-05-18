use std::path::Path;
use subprocess::Exec;
use swh_repo_mining::file_finder::{main, CliArgs, SearchBy};
use tempfile::TempDir;

// External dependencies: zstdcat, grep, jq

fn run_main(
    mode: SearchBy,
    dataset: &str,
    regex: &str,
    ignore_case: bool,
    rec_dirs: usize,
    limit: Option<usize>,
) -> TempDir {
    let out_dir = TempDir::new().unwrap();
    main(&CliArgs {
        mode,
        graph: Path::new(&format!("testdata/data/{dataset}/compressed/graph")).to_path_buf(),
        regex: regex.to_owned(),
        ignore_case,
        rec_dirs,
        with_swhids: true,
        with_filenames: true,
        limit,
        outdir: out_dir.path().to_path_buf(),
    })
    .unwrap();

    out_dir
}

#[test]
fn test_find_by_origin() {
    let out_dir = run_main(
        SearchBy::Origin,
        "2024-08-23-popular-4-shell",
        r"^readme\.*",
        true,
        0,
        None,
    );
    let readme_matches = {
        Exec::shell(format!("zstdcat {}/*.zst", out_dir.path().display())) | Exec::shell("wc -l")
    }
    .capture()
    .unwrap()
    .stdout_str();
    assert_eq!(readme_matches.trim(), "4");

    assert!({
        Exec::shell(format!("zstdcat {}/*.zst", out_dir.path().display()))
            // SWHID and name of oh-my-zsh's README file
            | Exec::shell(r"grep swh:1:ori:2a5b5491.*swh:1:rev:b0204f78.*swh:1:cnt:0f20fd06.*README\.md")
    }
    .capture()
    .unwrap()
    .success());

    // -------------------------------------------------------------------------

    let out_dir = run_main(
        SearchBy::Origin,
        "2024-08-23-popular-4-shell",
        r"^affective_com",
        false,
        0,
        None,
    );
    let matches = {
        Exec::shell(format!("zstdcat {}/*.zst", out_dir.path().display())) | Exec::shell("wc -l")
    }
    .capture()
    .unwrap()
    .stdout_str();
    assert_eq!(matches.trim(), "1");
}

#[test]
fn test_find_by_origin_rec() {
    fn run_rec(rec_dirs: usize) -> TempDir {
        run_main(
            SearchBy::Origin,
            "2024-08-23-popular-4-shell",
            r"\.z?sh$",
            true,
            rec_dirs,
            None,
        )
    }
    fn count_files(out_dir: TempDir) -> String {
        {
            Exec::shell(format!("zstdcat {}/*.zst", out_dir.path().display()))
                | Exec::shell("jq --raw-output '.matches_info[][1]'")
                | Exec::shell("wc -l")
        }
        .capture()
        .unwrap()
        .stdout_str()
        .trim()
        .to_owned()
    }

    assert_eq!(count_files(run_rec(0)), "6");
    assert_eq!(count_files(run_rec(1)), "6");
    assert_eq!(count_files(run_rec(5)), "36");
    assert_eq!(count_files(run_rec(1000)), "358");
}

#[test]
fn test_limit() {
    let out_dir = run_main(
        SearchBy::Origin,
        "2024-12-06-popular-10-shell",
        r"^readme\.*",
        true,
        0,
        Some(5),
    );
    let readme_matches = {
        Exec::shell(format!("zstdcat {}/*.zst", out_dir.path().display())) | Exec::shell("wc -l")
    }
    .capture()
    .unwrap()
    .stdout_str();
    assert_eq!(readme_matches.trim(), "5");
}

#[test]
fn test_find_by_directory() {
    let out_dir = run_main(
        SearchBy::Directory,
        "2024-08-23-popular-4-shell",
        r"^rust\.plugin\.zsh$",
        false,
        0,
        None,
    );
    let matches = {
        Exec::shell(format!("zstdcat {}/*.zst", out_dir.path().display())) | Exec::shell("wc -l")
    }
    .capture()
    .unwrap()
    .stdout_str();
    assert_eq!(matches.trim(), "6");

    assert!({
        Exec::shell(format!("zstdcat {}/*.zst", out_dir.path().display()))
            // SWHID and parent dir of oh-my-zsh's rust plugin (some version of)
            | Exec::shell(r"grep swh:1:cnt:c7f86c1224b62f241078445ae0fcb601bfc00064.*rust\.plugin\.zsh")
    }
    .capture()
    .unwrap()
    .success());
}
