# SWH List of Requirements

## Repository structure (tree)

- Target Commit for Extraction: Extract the tree structure from the most recent commit pointed to by the HEAD of each repository. This includes all directory contents that are reachable recursively from the directory pointed to by this commit.
- Content Details: Include all folder and file names within this directory structure, along with their respective file extensions. A list of repositories with the origin SHW IDs to be mined is provided, the list contain only repositories with at least 1 topic.
- Encoding Requirements: every field must be encoded in utf-8 before compiling the json file. Discard what do not pass the encoding.
- Particular cases: do not track the symlink, just take the name. Keep the name of the empty directories.

## README files

- Extract the content of the Readme file or all Readme files from the repository, searching among the following file name variations regexp:  /readme(\.(md|txt|rst))?/i

- In case of opting for file extraction, it is suggested to save the files using their hash. Subsequently, a reference table of the type: id_origin | readme_hash  would be necessary.
- The content of the readme file must be encoded in utf-8
- The max size of the readme should be the one used by software heritage = 100MiB

## JSON --- "schema"

```
{
  "unique_id": {                           // origin ID from SWH
    "readme": "hash or URL",               // Hash to a README file
    "contents": [                          // Contains child objects if the type is "directory", not present for files or symlinks
      "child_name": {                        // name for the child object 
        // Child object follows the same structure rules as described
      }
    ]
  }
}
```

## JSON --- example

```
{
  "origin_id1": {
    "readme": "hash_readme",
    "contents": [
      {
        "folder1": {
          "contents": [
            {
              "subfolder1": {
                "contents": ["file1.txt"]
              }
            },
            "file2.txt"
          ]
        }
      }
    ]
  },
  "origin_id2": {
    "readme": "hash_readme",
    "contents": ["link_1"]
  }
}
```
