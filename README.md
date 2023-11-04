# SPARROW (Synthesis Planning And Rewards-based Route Optimization Workflow)

A workflow to simultaneously select molecules and their synthetic routes for lead optimization and design-make-test cycles. This optimization approach aims to minimize synthetic cost while selecting the molecules that are most likely to fulfill design constraints.  

## Overview 
This repository performs the following steps: 
1. Performs a tree search to identify synthetic routes for a set of provided candidate molecules using ASKCOS 
2. Combines synthetic routes for all molecules into one synthesis network (defined as a **RouteGraph** object).
3. Calculates confidence scores for all reactions in the network using the ASKCOS forward predictor. These scores indicate the confidence of the model in the success of the reaction and serve as a proxy to estimate the likelihood that the reaction will succeed. 
4. Defines optimization problem variables using PuLP
5. Sets relevant constraints on the optimization variables and sets the objective function. 
6. Solves optimization problem with Gurobi.  
7. Visualizes the resulting selected routes and target molecules. 

## Table of Contents 
- [Overview](#overview)
- [Installation](#installation)
- [Requirements](#requirements)
- [Running SPARROW](#running-sparrow)
- [Future Goals](#future-goals)
- [Reproducing Results](#reproducing-results)

## Requirements 
To use ASKCOS to perform retrosynthesis searches, propose conditions, and score reactions, an API address to a deployed version of ASKCOS is required. Directions to deploy ASKCOS can be found [here](https://github.com/ASKCOS/ASKCOS). A ChemSpace API key is required use ChemSpace to assign compound buyability and cost. Refer to [these directions](https://api.chem-space.com/docs/#:~:text=Get%20API%20Key&text=The%20API%20key%20is%20unique,%40chem%2Dspace.com.) to attain the key. The key should be entered into the [keys.py](keys.py) file, and the path to this file is required to run SPARROW with ChemSpace. 

## Installation 
Create conda environment using [mamba](https://mamba.readthedocs.io/en/latest/installation.html) and install additional requirements through pip. 

```
mamba env create -f environment.yml
conda activate sparrow
pip install -r requirements.txt
```
Finally, install this package. 
```
python setup.py develop 
```

#### Installing Mamba
If on Linux with x86 cores: 
```
wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh
bash Mambaforge-Linux-x86_64.sh
```
Otherwise, use the correct link from [Mambaforge installation page](https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh).


## Running SPARROW
The general command to run SPARROW is:
`sparrow --target-csv <path/to/target_csv> --path-finder {api, lookup} --recommender {api, lookup} --coster {naive, chemspace} [additional arguments]`

Alternatively, you may run the following command: 
`sparrow --config <path/to/config>`
which directs SPARROW to a configuration file with all arguments. Some example config files are in the [examples folder](examples).

If more than one run is performed on the same set of compounds, and only the weighting factors are changed, the route graph information from the first run can be easily incorporated into following runs. By providing the path to the `trees_w_info.json` file from the initial run as the argument for `--graph`, all potential paths, compound costs, and reaction scores are incorporated. In these cases, entries for `--path-finder`, `--recommender`, `--scorer`, and `--coster` are not required. 

#### Settings 
 - `--config`: the filepath of the configuration file
 - `--target-csv`: the filepath of the target csv file
 - `--reward-weight`: weighting factor for reward objective
 - `--start-cost-weight`: weighting factor for starting material cost objective
 - `--reaction-weight`: weighting factor for reaction objective
 - `--output-dir`: where to save checkpoints files and paths generated by SPARROW
 - `--graph`: path to route graph json file. If provided, no route planning is performed
 - `--path-finder {lookup,api}`: type of tree builder to use
 - `--tree-lookup-dir`: path of lookup json file with combined retrosynthesis tree
 - `--time-per-target`: expansion time in seconds for each target
 - `--max-ppg`: maximum price per gram in dollars for starting materials for ASKCOS MCTS tree search
 - `--max-branching`: maximum branch factor for ASKCOS MCTS tree search
 - `--tree-host`: host address for tree builder, if using ASKCOS API path finder
 - `--recommender {lookup,local,api}`: type of context recommender to use
 - `--context-host`: host address for context recommender, if using API recommender
 - `--context-lookup`: path of lookup csv file for lookup context recommender
  - `--scorer {lookup,local,api}`: type of scorer to use
 - `--scorer-host`: host address for reaction scorer, if using API recommender
 - `--scorer-lookup`: path of reaction scorer csv file for lookup reaction scorer (not implemented yet)
 - `--coster {lookup, naive, chemspace}`: type of compound coster to use
 - `--key-path` path that includes the file keys.py with chemspace api key
 - `--coster-lookup`: path of lookup file for lookup cost and buyability

**A note about required arguments:** The only required argument in SPARROW in `--target-csv`. However, providing this alone will not be sufficient to run SPARROW. In addition to candidates and rewards, SPARROW's optimization requires a set of potential reactions and scores for each reaction. If a provided `--graph` argument corresponds to a file that includes both potential reactions as a retrosynthesis tree _and_ reaction scores, that is sufficient to run SPARROW. However, if the file only contains a retrosynthesis tree, without reaction scores, SPARROW will require a `--recommender` argument. Likewise, if no `--graph` is provided, a valid entry for `--path-finder` (and any corresponding arguments) are required. We are currently working on expanding the documentation for SPARROW and improving its usability.


##  Optimization Problem Formulation 
The formulation of the optimization problem can be found at our preprint (link to be added shortly). 

## Reproducing Results
The results shown in our [preprint]() can be reproduced using the [optimize_preprint](scripts/optimize_preprint.py) script. This uses SPARROW to select routes from previously generated retrosynthesis trees with previously computed conditions and reaction scores. For each case study, this information is stored in the relevant [examples folder](examples) as a `trees_w_info.json` file. Two configuration files exist for each example: a `config_opt.ini` that builds a route graph from the existing `trees_w_info.json` file, and a `config.ini` that builds a route graph from scratch using ASKCOS. In order to use the sample `config.ini` files, you must enter an IP address corresponding to an ASKCOS instance where indicated. 

## Future Goals
1. Incorporate reaction conditions into objective function 
2. Update tree visualization
3. Modify optimization function formulation to better capture information gain and cost 



