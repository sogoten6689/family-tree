import os
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network


def draw_static_png(G: nx.MultiDiGraph, output_path: str = "output/family_tree.png") -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    simple_G = nx.DiGraph()
    for n, attrs in G.nodes(data=True):
        simple_G.add_node(n, **attrs)

    for u, v, attrs in G.edges(data=True):
        rel = attrs.get("relation_type", "")
        if simple_G.has_edge(u, v):
            old_rel = simple_G[u][v].get("relation_type", "")
            if old_rel != "parent_of" and rel == "parent_of":
                simple_G[u][v]["relation_type"] = rel
        else:
            simple_G.add_edge(u, v, relation_type=rel)

    pos = nx.spring_layout(simple_G, seed=42)
    labels = {n: f"{simple_G.nodes[n].get('full_name', n)}\n({n})" for n in simple_G.nodes}
    edge_labels = {(u, v): d.get("relation_type", "") for u, v, d in simple_G.edges(data=True)}

    plt.figure(figsize=(12, 8))
    nx.draw(simple_G, pos, with_labels=False, node_size=2200, font_size=8, arrows=True)
    nx.draw_networkx_labels(simple_G, pos, labels=labels, font_size=8)
    nx.draw_networkx_edge_labels(simple_G, pos, edge_labels=edge_labels, font_size=7)

    plt.title("Family Graph")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def draw_interactive_html(G: nx.MultiDiGraph, output_path: str = "output/family_tree.html") -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    net = Network(height="800px", width="100%", directed=True)
    net.barnes_hut()

    for node_id, attrs in G.nodes(data=True):
        label = attrs.get("full_name", node_id)
        title = (
            f"ID: {node_id}<br>"
            f"Name: {attrs.get('full_name')}<br>"
            f"Gender: {attrs.get('gender')}<br>"
            f"Birth: {attrs.get('birth_year')}<br>"
            f"Death: {attrs.get('death_year')}"
        )
        net.add_node(node_id, label=label, title=title)

    for u, v, attrs in G.edges(data=True):
        rel = attrs.get("relation_type", "")
        conf = attrs.get("confidence", 1.0)
        title = f"type={rel}, confidence={conf}"
        net.add_edge(u, v, label=rel, title=title)

    net.save_graph(output_path)
