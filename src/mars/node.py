from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, Iterable, Optional, List

class Node(ABC): 
    """
    A Node is one node of a RouteGraph
    """

    def __init__(self, 
                 smiles: str, 
                 parents: Optional[List] = None, 
                 children: Optional[List] = None,
                 **kwargs) -> None:
        self.smiles = smiles
        self.parents = {}
        if parents: 
            self.update(parents=parents)

        self.children = {}
        if children: 
            self.update(children=children)

        self.selected = 0
        self.id = 0

    def update(self, parents=None, children=None): 
        """ Adds children and parents to node """

        if parents:
            for parent in parents: 
                self.parents[parent.smiles] = parent 
        
        if children: 
            for child in children: 
                self.children[child.smiles] = child

        return 
