"""Seed the supplier_customer and competitor edges read-throughs need.

`supplier_customer` and `competitor` have been declared edge types since the
graph was introduced and have never had a single instance, which is why no
displacement read-through could fire: the graph knew that Google matters to
our electronics sector, but not that Broadcom sells to Google or that Marvell
competes with Broadcom, so "Google taps Marvell" led nowhere.

These are curated relationships, entered the same way the anchor_demand edges
were -- stated, dated, and marked `curated` so a reader can tell them from
anything harvested automatically. They are deliberately few. Each one is a
claim the dashboard will reason from, and a wrong edge produces a confident
wrong conclusion, which is worse than no conclusion.

Scope: the global semiconductor and electronics supply chain, because that is
where this book's manufacturing_electronics, semiconductors_equipment and
data_center_support holdings take their second-order exposure. Run once;
re-running is harmless, as existing edges are never duplicated.

    python scripts/seed_read_through_edges.py
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.entity_graph import (  # noqa: E402
    _edge_key,
    load_entity_graph,
    save_entity_graph,
)

TODAY = datetime.date.today().isoformat()

# Who sells to whom. Direction is src -> dst, "src supplies dst".
SUPPLIER_CUSTOMER = [
    ("Broadcom", "Google", "Custom AI accelerator (TPU) silicon and networking"),
    ("Broadcom", "Meta", "Custom accelerator and networking silicon"),
    ("TSMC", "Apple", "Leading-edge foundry for A-series and M-series silicon"),
    ("TSMC", "Nvidia", "Leading-edge foundry for datacentre GPUs"),
    ("TSMC", "Qualcomm", "Leading-edge foundry"),
    ("Samsung", "Apple", "Memory and display supply"),
    ("Micron", "Apple", "DRAM and NAND supply"),
    ("Micron", "Nvidia", "High-bandwidth memory for datacentre GPUs"),
    ("SK Hynix", "Nvidia", "High-bandwidth memory for datacentre GPUs"),
    ("Foxconn", "Apple", "Contract assembly, including Indian plants"),
]

# Who competes with whom. Undirected in meaning; stored both ways is
# unnecessary because the read-through engine checks the pair in either order.
COMPETITOR = [
    ("Marvell", "Broadcom", "Custom silicon and datacentre networking"),
    ("Marvell", "Nvidia", "Datacentre interconnect"),
    ("AMD", "Nvidia", "Datacentre accelerators"),
    ("Intel", "TSMC", "Foundry services"),
    ("Samsung", "TSMC", "Foundry services"),
    ("SK Hynix", "Micron", "DRAM and high-bandwidth memory"),
    ("Samsung", "Micron", "DRAM and NAND"),
    (
        "CXMT",
        "Micron",
        "Commodity DRAM; the Chinese entrant filling AI-driven shortage",
    ),
    ("CXMT", "Samsung", "Commodity DRAM"),
    ("CXMT", "SK Hynix", "Commodity DRAM"),
]

# Entities that matter to a read-through chain but are not themselves demand
# anchors for any sector we hold. Without an edge of some kind they are
# invisible to graph_entities() and the chain breaks at the first hop.
#
# Memory makers route to manufacturing_electronics because that is where a
# memory price move lands in this book -- the EMS and device assemblers who
# buy the parts, not the chipmakers we do not own.
ANCHOR_DEMAND = [
    ("Marvell", "semiconductors_equipment", "Custom silicon demand anchor"),
    ("Meta", "data_center_support", "Hyperscale datacentre capex anchor"),
    ("Microsoft", "data_center_support", "Hyperscale datacentre capex anchor"),
    ("Amazon", "data_center_support", "Hyperscale datacentre capex anchor"),
    ("Google", "data_center_support", "Hyperscale datacentre capex anchor"),
    ("SK Hynix", "manufacturing_electronics", "Memory supply into device assembly"),
    ("CXMT", "manufacturing_electronics", "Memory supply into device assembly"),
    ("Foxconn", "manufacturing_electronics", "Contract assembly anchor in India"),
]

# Input keywords the graph did not carry. "memory chip" was there; the words
# actually used in headlines were not, and a headline reading "RAM shortage"
# routed nowhere.
INPUT_COST = [
    ("DRAM", "manufacturing_electronics"),
    ("NAND", "manufacturing_electronics"),
    ("RAM", "manufacturing_electronics"),
    ("memory", "manufacturing_electronics"),
    ("memory", "data_center_support"),
    ("HBM", "data_center_support"),
    ("HBM", "semiconductors_equipment"),
]


def main():
    graph = load_entity_graph()
    existing = {_edge_key(e) for e in graph.get("edges", [])}
    added = 0

    def add(src, dst, etype, note=""):
        nonlocal added
        edge = {
            "src": src,
            "dst": dst,
            "type": etype,
            "evidence": "curated",
            "added": TODAY,
        }
        if note:
            edge["note"] = note
        if _edge_key(edge) in existing:
            return
        existing.add(_edge_key(edge))
        graph.setdefault("edges", []).append(edge)
        added += 1

    for src, dst, note in SUPPLIER_CUSTOMER:
        add(src, dst, "supplier_customer", note)
    for src, dst, note in COMPETITOR:
        add(src, dst, "competitor", note)
    for src, dst, note in ANCHOR_DEMAND:
        add(src, dst, "anchor_demand", note)
    for src, dst in INPUT_COST:
        add(src, dst, "input_cost")

    if added:
        save_entity_graph(graph)
    print(f"Added {added} edge(s); graph now holds {len(graph['edges'])}.")

    counts = {}
    for e in graph["edges"]:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    for etype, n in sorted(counts.items()):
        print(f"  {etype:20} {n}")


if __name__ == "__main__":
    main()
