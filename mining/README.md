Mining of the [Software Heritage][swh] [archive][swh-archive] to find repositories with "signals" of art-related code is done in two main steps.

[swh]: https://www.softwareheritage.org/
[archive]: https://archive.softwareheritage.org/

1) Retrieve the [Software Heritage Graph Dataset][graph-dataset], version 2025-05-18, in compressed graph form, from: <https://datasets.softwareheritage.org/graphs/compressed/#2025-05-18-compressed>

[graph-dataset]: https://datasets.softwareheritage.org/graphs/compressed/

As documented on the website, the dataset can be downloaded as follows:

    $ aws s3 cp --recursive --no-sign-request s3://softwareheritage/graph/2025-05-18/compressed/ 2025-05-18-compressed
    # OR
    $ swh datasets download-graph 2025-05-18

2) Mine the graph to find filename patterns that correspond to the art "signals" documented in the paper, using the [Software Heritage repository mining toolkit][mining-toolkit].
The version of the toolkit we used in our experiment (commit [swh:1:rev:d9412b0d5c9ebe4c907b27aa84084382309ce92e](http://archive.softwareheritage.org/swh:1:rev:d9412b0d5c9ebe4c907b27aa84084382309ce92e)) is included in this reproducibility package for convenience.

[mining-toolkit]: https://gitlab.com/zacchiro/swh-repo-mining

To build the toolkit, first install a suitable Rust toolchain (e.g., via [rustup][rustup]) then build the `find-files` binary:

    $ cd mining/swh-repo-mining/
	$ cargo build --release --bin=find-files
	$ target/release/find-files --help | head -n 3
	Find directory entries with names matching a given regular expression in the entire Software Heritage graph
    
    Usage: find-files [OPTIONS] --graph <BASENAME> --pattern <REGEX> --outdir <DIR>

[rustup]: https://rustup.rs/
    
To actually perform the mining:

    $ outdir=/somewhere/art-mining
	$ cargo run --release --bin=find-files -- --graph /dataset/location/2025-05-18/compressed/graph --outdir $outdir/ --by origin --with-swhids --with-filenames --recursive 1024 --pattern '(\.(pde|scd|ndbx|toe|tox|v4p|clj)$)|(^ofApp\.(cpp|h)$)|(^fxhash\.min\..*$)|(^p5\.(js|min\.js)$)' 2> $outdir.log

This will create multiple compressed NDJSON files (one per CPU core) in the `$outdir` directory, that can be concatenated together into a single file to obtain the input dataset for the next experimental steps described in the paper.
