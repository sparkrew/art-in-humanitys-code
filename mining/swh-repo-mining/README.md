Software Heritage repository mining toolkit (in Rust)
====

This repository contains a collection of repository mining tools, to be run on the [Software Heritage archive][swh] to respond to various needs, ranging from scientific investigation of public code production to specific needs in the fields of empirical software engineering (EMSE) and mining software repositories (MSR).

[swh]: https://www.softwareheritage.org/

The entry point of each tool is a main program located in the `src/bin/` directory.

Mining tools are implemented in [Rust][rust] using the [swh-graph-rs API][swh-graph-rs], which is exposed by the [compressed graph representation][swh-graph] of the Software Heritage archive.

[rust]: https://www.rust-lang.org/
[swh-graph-rs]: https://docs.rs/swh-graph/latest/swh_graph/
[swh-graph]: https://docs.softwareheritage.org/devel/swh-graph/

In order to run the mining tools you need a local copy of the swh-graph dataset.
You can obtain one from a number of public cloud hosting places, usually under the respective open dataset programs.
See the documentation of [Software Heritage datasets][swh-dataset] for details, links, and download instructions.

[swh-dataset]: https://docs.softwareheritage.org/devel/swh-export/


Test data
----

Test data is available from a [separate repository][swh-repo-mining-data], linked to this one as a Git submodule.

[swh-repo-mining-data]: https://gitlab.com/zacchiro/swh-repo-mining-data

To be able to run tests either clone this repository recursively (`git clone --recurse-submodules`), or populate submodules afterwards with `git submodule update --init`.


Maintainer
----

[Stefano Zacchiroli][maint-homepage] [`<zack@upsilon.cc>`][maint-email]

[maint-homepage]: https://upsilon.cc/~zack
[maint-email]: mailto:zack@upsilon.cc


License
----

GNU General Public License, version 3.0 or above.
See the file `LICENSE-GPL-3.0-or-later` for details.


Citation
----

If you use this code for your research work, please acknowledge it by citing the papers that made it possible:

Paolo Boldi, Antoine Pietri, Sebastiano Vigna, Stefano Zacchiroli.  
[Ultra-Large-Scale Repository Analysis via Graph Compression](https://ieeexplore.ieee.org/document/9054827).  
In proceedings of SANER 2020: The 27th IEEE International Conference on Software Analysis, Evolution and Reengineering, pages 184-194.  
IEEE 2020.

Tommaso Fontana, Sebastiano Vigna, Stefano Zacchiroli.  
[WebGraph: The Next Generation (Is in Rust)](https://dl.acm.org/doi/abs/10.1145/3589335.3651581).  
In proceedings of WWW’24: The ACM Web Conference 2024. Pages 686-689.  
ACM 2024.
