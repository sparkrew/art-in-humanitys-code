# RQ3

## /data/

The data folder includes:

- `p5_libraries.txt`:  The list of p5 library names extracted from the documentation. 
- `74_examples_manual_classification.json`: First sample of 74 sketches manually labeled independently by two authors, in order to prepare and refine the prompt.
- `manual_annotation_50.json`: Second round of manual annotation of 50 sketches to assess the quality of the prompt.
- `llm_labels_and_metadata.json`: List of 17875 sketches annotated with the following data:
  - LLM generated labels.
  - list of p5 libraries.
  - list of external artifacts.
  - number of lines of code.
- `gen-art-classification.md`: List of characteristics that we define to capture different practices in p5.

## /scripts/

The scripts folder includes:

- `plot_entities_label_prediction_fig7a.py`: The script fetches data from `llm_labels_and_metadata.json` using the 'material_and_process' category to generate the Material and Processes bar plot in RQ3.
- `plot_libraries_assets_venn_diagram_fig7b.py`: The script fetches data from `llm_labels_and_metadata.json`, using the external artifacts usage in the sketches in order to generate the venn diagram plot.
- `plot_4_quadrants_fig7c.py`: The script fetches data from `llm_labels_and_metadata.json` using the 'interaction' and 'outcome' categories to generate the four quadrants plot.
- `random_p5_repos.py`: The script to randomly sample 1% of the repositories related to p5.js.
- `prompt.py`: The prompt for the LLM-based characterization of the p5 sketches.
- `run_predictions.py` and `start-qwen3.sh`: The scripts to run the LLM-based characterization of the p5 sketches on the [calcul québec](https://www.calculquebec.ca/) computing infrastructure.
- `process_predictions.py`: The script used to analyze the outcome of the LLM.
