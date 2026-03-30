import networkx as nx
from typing import List
from src.models import Person, Relationship


def build_family_graph(people: List[Person], relationships: List[Relationship]) -> nx.MultiDiGraph:
  
    G = nx.MultiDiGraph()

    for p in people:
        G.add_node(
            p.id,
            full_name=p.full_name,
            gender=p.gender,
            birth_year=p.birth_year,
            death_year=p.death_year,
        )

    for r in relationships:
        G.add_edge(
            r.from_id,
            r.to_id,
            relation_type=r.type,
            source=r.source,
            confidence=r.confidence,
        )

        if r.type in {"spouse_of", "sibling_of"}:
            G.add_edge(
                r.to_id,
                r.from_id,
                relation_type=r.type,
                source=r.source,
                confidence=r.confidence,
            )

    return G
