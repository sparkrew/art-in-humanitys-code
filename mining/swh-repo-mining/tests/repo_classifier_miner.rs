use std::path::Path;
use subprocess::Exec;
use swh_repo_mining::repo_classifier_miner::main;
use tempfile::TempDir;

#[test]
fn test_repo_classifier_miner() {
    let out_dir = TempDir::new().unwrap();
    let out_path = out_dir.path();

    main(
        Path::new("testdata/data/2024-08-23-popular-4-shell/compressed/graph").to_path_buf(),
        None,
        out_path.to_path_buf(),
    )
    .unwrap();

    let mined_origins =
        { Exec::shell(format!("zstdcat {}/*.zst", out_path.display())) | Exec::shell("wc -l") }
            .capture()
            .unwrap()
            .stdout_str();
    assert_eq!(mined_origins.trim(), "4");

    assert!({
        Exec::shell(format!("zstdcat {}/*.zst", out_path.display()))
            | Exec::shell(
                "grep swh:1:ori:201c1ca7bb9d432f0d054c17aa951c6b2a428132.*d3-delaunay.*voronoi.md",
            )
    }
    .capture()
    .unwrap()
    .success());

    assert!({
        Exec::shell(format!("zstdcat {}/*.zst", out_path.display()))
            | Exec::shell(
                "grep swh:1:ori:e40520157fa67a689e8f4723de524614fd347441.*papers-we-love/papers-we-love.*swh:1:cnt:67ad19be09c1e30a31f0a46ec9052a19a9d285ef",
            )
    }
    .capture()
    .unwrap()
    .success());
}
