import os, sys
sys.path.append('/home/jfromer/sparrow/askcos-core') # change this for your system to where askcos folder is located
sys.path.append('/home/jfromer/sparrow/')

import json 
import pandas as pd 
from typing import Dict, List
from tqdm import tqdm
from pathlib import Path
from sparrow.tree_build_utils import get_paths
from sparrow.json_utils import storage_from_api_response, save_storage_dict 
from sparrow.route_graph import RouteGraph
from sparrow.route_selector import RouteSelector
from sparrow.scorer import AskcosAPIScorer
from sparrow.condition_recommender import AskcosAPIRecommender
from sparrow.coster import ChemSpaceCoster
from sparrow.visualizer import Visualizer
from keys import chemspace_api_key

def make_target_dict() -> Dict: 
    target_dict = {
        "COC5=CC(N=CN=C6NC7=CC=CC(OC)=C7)=C6C=C5OC" : 3,
        "COC1=CC(N=CN=C2NC3=CC=C(OCC4=CC=CC=C4)C=C3)=C2C=C1OC" : 4,
        "COC8=CC(N=CN=C9NC%10=CC=CC(Cl)=C%10)=C9C=C8OC" : 2,
        "COC%11=CC(N=CN=C%12NC%13=CC=CC(O)=C%13)=C%12C=C%11OC" : 11,
        "COC%14=CC(N=CN=C%15NC%16=CC=C(NC(C%17=CC=CC=C%17)=O)C=C%16)=C%15C=C%14OC" : 14,
    }
    return target_dict, list(target_dict.keys())

def add_contexts_scores_to_trees(json_file: str, target_dict: str, base_dir, host: str = None) -> None: 
    graph = RouteGraph(node_filename=json_file)

    selector = RouteSelector(
        target_dict=target_dict,
        route_graph=graph, 
        condition_recommender=AskcosAPIRecommender(host=host), 
        output_dir=base_dir,
        rxn_scorer=AskcosAPIScorer(host=host),
    )

    selector.graph.to_json(base_dir/'trees_w_context_scores.json')

    return selector

def cost_compounds(json_file: str, target_dict: Dict, base_dir):
    graph = RouteGraph(node_filename=json_file)

    selector = RouteSelector(
        target_dict=target_dict,
        route_graph=graph, 
        condition_recommender=None, # already in graph   
        rxn_scorer=None,     # already in graph      
        coster=ChemSpaceCoster(api_key=chemspace_api_key),
        output_dir=base_dir,
    )
    selector.graph.to_json(base_dir/'trees_w_context_scores_costs.json')
    return 

def optimize(json_file: str, target_dict: Dict, base_dir):
    graph = RouteGraph(node_filename=json_file)
    
    selector = RouteSelector(
        target_dict=target_dict,
        route_graph=graph, 
        condition_recommender=None, # already in graph
        rxn_scorer=None, # already in graph       
        coster=None, # already in graph 
        output_dir=base_dir,
        remove_dummy_rxns_first=True, 
        weights=[1,1,1]
    )
    selector.define_variables()
    selector.set_objective()
    selector.set_constraints()
    selector.optimize(solver=None) # solver='GUROBI' for GUROBI (license needed)

    return selector 

def extract_vars(selector: RouteSelector, base_dir): 
    nonzero_vars = [
            var for var in selector.problem.variables() if var.varValue > 0.01
        ]
    rxn_ids = [var.name.split('_')[1] for var in nonzero_vars if var.name.startswith('rxn')]
    mol_ids = [var.name.split('_')[1] for var in nonzero_vars if var.name.startswith('mol')]

    selected_targets = set(mol_ids) & set(selector.targets)
    starting_mats = set([node.id for node in selector.graph.buyable_nodes()])
    selected_starting = set(mol_ids) & starting_mats
    print(f'{len(selected_targets)} targets selected using {len(rxn_ids)} reactions and {len(selected_starting)} starting materials')

    storage = {}
    for target in selected_targets: 
        store_dict = {'Compounds':[], 'Reactions':[]}
        smi = selector.graph.smiles_from_id(target)
        storage[smi] = find_mol_parents(store_dict, target, mol_ids, rxn_ids, selector.graph)
        storage[smi]['Reward'] = selector.target_dict[target]

    with open(base_dir/f'routes_{len(selected_targets)}tars.json','w') as f: 
        json.dump(storage, f, indent='\t')

    return storage 

def find_rxn_parents(store_dict, rxn_id, selected_mols, selected_rxns, graph): 
    par_ids = [n.id for n in graph.node_from_id(rxn_id).parents.values()]
    selected_pars = set(par_ids) & set(selected_mols)
    for par in selected_pars: 
        store_dict['Compounds'].append(graph.smiles_from_id(par))
        store_dict = find_mol_parents(store_dict, par, selected_mols, selected_rxns, graph)
    return store_dict

def find_mol_parents(store_dict, mol_id, selected_mols, selected_rxns, graph): 
    par_ids = [n.id for n in graph.node_from_id(mol_id).parents.values()]
    selected_pars = set(par_ids) & set(selected_rxns)
    for par in selected_pars: 
        node = graph.node_from_id(par)
        if node.dummy: 
            store_dict['Reactions'].append({
                'smiles': node.smiles,
                'starting material cost ($/g)': selector.cost_of_dummy(node), 
            })
        else: 
            store_dict['Reactions'].append({
                'smiles': node.smiles,
                'conditions': node.get_condition(1)[0], 
                'score': node.score,
            })
        store_dict = find_rxn_parents(store_dict, par, selected_mols, selected_rxns, graph)
    return store_dict

def get_trees(targets, base_dir, time_per_target=60, max_branching=str(20), host='https://18.4.94.12'):
    params = {
        'buyable_logic': 'or',
        'max_depth': '10',
        'expansion_time': str(time_per_target),
        'max_ppg': '100',
        'return_first': 'false', 
        'max_branching': max_branching,
    }

    results = get_paths(targets, host=host, store_dir=base_dir/'paths', params=params)

    return results 

def combine_outputs(result_ls: List[Path], path_dir: Path):

    trees = {}
    for p in tqdm(result_ls, desc='Combining ASKCOS outputs'): 
        with open(p,'r') as f: 
            entry = json.load(f)
        for smi, path in entry.items(): 
            if 'output' in path and len(path['output'])>0: 
                trees[smi] = {"result": path} 
    
    with open(path_dir/'askcos_outputs.json','w') as f: 
        json.dump(trees, f, indent='\t')

    return trees

def process_tree(trees: Dict = None, tree_file: Path = None) -> Dict: 
    if trees is None: 
        with open(tree_file, 'r') as f: 
            trees = json.load(f)
    

    storage = None
    for response in tqdm(trees.values(), desc='Reading ASKCOS API results'):
        storage = storage_from_api_response(response, storage)

    return storage 


if __name__=='__main__': 
    base_dir = Path('examples/small_scale')
    path_dir = base_dir/'paths'
    host = 'https://3.139.77.247/'

    target_dict, targets = make_target_dict()
    # get_trees(targets, base_dir, time_per_target=30, host=host)
    
    paths_ls = list(path_dir.glob('paths*'))
    trees = combine_outputs(paths_ls, base_dir)
    tree_file = list(base_dir.glob('*outputs*'))[0]
    storage = process_tree(tree_file=tree_file)
    save_storage_dict(storage, base_dir/'trees.json')

    selector = add_contexts_scores_to_trees(base_dir/'trees.json', target_dict, base_dir, host=host)
    selector = cost_compounds(base_dir/'trees_w_context_scores.json', target_dict, base_dir)
    selector = optimize(base_dir/'trees_w_context_scores_costs.json', target_dict, base_dir)
    storage = extract_vars(selector, base_dir)
    print('done')

    # 61 targets selected using 122 reactions and 61 starting materials