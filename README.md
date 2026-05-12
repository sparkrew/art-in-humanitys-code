# art-in-humanitys-code

- dataset
  - script to clean scd (roxana)
  - script to deduplicate (yogya)
  - jq + notebook (nadia)
- RQ1 (nadia)
  - 1 script to get the forks (yogya)
  - 2 scripts to check live or dead
  - one jq query
  - notebook for the figure 4
- RQ2 (yogya, lena)
  - smapling script: select random json sample 
  - GH query script: collect data from GH to have rich sample
  - script to query geoapify
  - script to reverse query geoapify for countries? depends on final map choices
  - json for the sample (&data cleaning part 1)
  - script to simplify the data
  - notebook to clean (part 2)
  - json used for the map
  - notebook for the map
- RQ3
- RQ4 (yogya, roxana)
  - script to get top 42
  - 42top.json
  - topics-notes.csv
- python script to generate the plot

Programming frameworks for the arts and their corresponding filename patterns:

| Art Programming Env. | Language | Filename pattern |
|---|---|---|
| [p5.js](https://github.com/processing/p5.js) | JavaScript | `p5.js`, `p5.min.js` |
| [openFrameworks](https://github.com/openframeworks/openFrameworks) | C++ | `ofApp.cpp`, `ofApp.h` |
| [Processing](https://github.com/processing/processing4/) | Java | `.pde` |
| [supercollider](https://github.com/supercollider/supercollider) | C++ | `.scd` |
| [TouchDesigner](https://derivative.ca/UserGuide/TouchDesigner) | node-based + Python | `.toe`, `.tox` |
| [nodebox](https://github.com/nodebox/nodebox) | node-based + Python or Clojure | `.ndbx` |
| [vvvv](https://github.com/vvvv) | node-based + C# | `.v4p` |