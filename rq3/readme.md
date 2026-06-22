The data folder includes:
 - the initial list of p5 sketches randomly sampled from our dataset
 - the list of names of p5 libraries
 - the list of characteristics that we define to capture different practices in p5
 - the final list of files annotated with LLM-based generated labels, the list of external artifacts it relies on, and the list of p5 libraries it uses
   
The scripts folder includes
 - the script to randomly sample 1% of the repositories related to p5.js
 - the prompt for the LLM-based characterization of the p5 sketches
 - the scripts to run the LLM-based characterization of the p5 sketches on the [calcul québec](https://www.calculquebec.ca/) computing infrastructure
 - the script to collect the artifacts and libraries in the sketch folders
 - the scripts to generate the plots in the paper
