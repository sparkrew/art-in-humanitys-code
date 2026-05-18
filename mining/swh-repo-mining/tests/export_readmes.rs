#![cfg(feature = "deprecated-binaries")]

use std::path::Path;
use subprocess::Exec;
use swh_repo_mining::export_readmes::main;
use tempfile::TempDir;

#[test]
fn test_readme_mining() {
    let out_dir = TempDir::new().unwrap();
    let out_path = out_dir.path();
    main(
        Path::new("testdata/data/2024-12-06-popular-10-shell/compressed/graph").to_path_buf(),
        out_path.to_path_buf(),
    )
    .unwrap();

    let origins_w_readme =
        { Exec::shell(format!("zstdcat {}/*.csv.zst", out_path.display())) | Exec::shell("wc -l") }
            .capture()
            .unwrap()
            .stdout_str();
    assert_eq!(origins_w_readme.trim(), "9");

    let ohmyzsh_readme = {
        Exec::shell(format!(
            "zstdgrep --no-filename ohmyzsh {}/*.csv.zst",
            out_path.display()
        )) | Exec::shell("cut -f 1 -d,")
    }
    .capture()
    .unwrap()
    .stdout_str();
    assert_eq!(
        ohmyzsh_readme.trim(),
        "swh:1:cnt:58828cf7f679c521012e5c7506157cc52767916b"
    );
}
