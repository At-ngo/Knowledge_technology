"""Small local inference demo for Module 4.

The script mimics the GenericRuleReasoner behaviour so we can validate
that the handcrafted rules produce the expected triples before wiring
Fuseki to the official rule file.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, Set, Tuple

from rdflib import Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
TRIPLE_PATH = ROOT / "legal_triples.ttl"

LEGAL = Namespace("http://example.org/legal-qa#")


def build_graph() -> Graph:
    graph = Graph()
    graph.parse(TRIPLE_PATH, format="turtle")
    return graph


def compute_transitive_closure(
    edges: DefaultDict[URIRef, Set[URIRef]]
) -> Dict[URIRef, Set[URIRef]]:
    """Forward-chain until all reachable nodes are registered."""
    changed = True
    while changed:
        changed = False
        for start, children in list(edges.items()):
            closure = set(children)
            for child in list(children):
                closure.update(edges.get(child, set()))
            if not closure.issubset(children):
                edges[start].update(closure)
                changed = True
    return edges


def infer_bao_gom(graph: Graph) -> int:
    edges: DefaultDict[URIRef, Set[URIRef]] = defaultdict(set)
    for s, o in graph.subject_objects(LEGAL.baoGom):
        edges[s].add(o)

    closure = compute_transitive_closure(edges)
    additions = 0
    for parent, members in closure.items():
        for member in members:
            triple = (parent, LEGAL.baoGom, member)
            if triple not in graph:
                graph.add(triple)
                additions += 1
    return additions


def infer_scope_from_members(graph: Graph) -> int:
    """Propagate apDungCho from a group down to every member of the group."""
    members: DefaultDict[URIRef, Set[URIRef]] = defaultdict(set)
    for s, o in graph.subject_objects(LEGAL.baoGom):
        members[s].add(o)

    full_members = compute_transitive_closure(members)
    additions = 0
    for holder, group in graph.subject_objects(LEGAL.apDungCho):
        for member in full_members.get(group, set()):
            triple = (holder, LEGAL.apDungCho, member)
            if triple not in graph:
                graph.add(triple)
                additions += 1
    return additions


def infer_violation_classes(graph: Graph) -> Tuple[int, int]:
    violation_additions = 0
    severe_additions = 0

    for actor, action in graph.subject_objects(LEGAL.cam):
        triple = (action, RDF.type, LEGAL.HanhViViPham)
        if triple not in graph:
            graph.add(triple)
            violation_additions += 1

    for action, label in graph.subject_objects(LEGAL.label):
        if isinstance(label, Literal) and "nồng độ cồn" in str(label).lower():
            triple = (action, RDF.type, LEGAL.SevereViolation)
            if triple not in graph:
                graph.add(triple)
                severe_additions += 1

    return violation_additions, severe_additions


def infer_article_mentions(graph: Graph) -> int:
    additions = 0
    banning_entities = defaultdict(set)
    for actor, action in graph.subject_objects(LEGAL.cam):
        banning_entities[actor].add(action)

    for article, entity in graph.subject_objects(LEGAL.mentionsEntity):
        for action in banning_entities.get(entity, set()):
            triple = (article, LEGAL.mentionsEntity, action)
            if triple not in graph:
                graph.add(triple)
                additions += 1
    return additions


def run_sparql(graph: Graph, label: str, query: str) -> None:
    print(f"\n=== {label} ===")
    rows = list(graph.query(query, initNs={"legal": LEGAL, "rdf": RDF}))
    if not rows:
        print("No rows returned")
    else:
        for row in rows:
            if isinstance(row, tuple):
                print(" - ", " | ".join(str(item) for item in row))
            else:  # ASK queries yield a bare boolean
                print(" - ", bool(row))


def main() -> None:
    graph = build_graph()
    print("Loaded graph with", len(graph), "triples")

    added_bao_gom = infer_bao_gom(graph)
    added_scope = infer_scope_from_members(graph)
    added_violation, added_severe = infer_violation_classes(graph)
    added_mentions = infer_article_mentions(graph)

    print("Added transitive baoGom triples:", added_bao_gom)
    print("Propagated apDungCho relationships:", added_scope)
    print("Tagged violations:", added_violation)
    print("Tagged severe alcohol cases:", added_severe)
    print("Linked articles to banned actions:", added_mentions)

    run_sparql(
        graph,
        "KetCauHaTangDuongBo indirectly contains Duong",
        """
        ASK {
          legal:KetCauHaTangDuongBo legal:baoGom legal:Duong .
        }
        """,
    )

    run_sparql(
        graph,
        "Information obligations apply to pedestrians",
        """
        SELECT ?holder WHERE {
          ?holder legal:apDungCho legal:NguoiDiBoTrenDuongBo .
        }
        LIMIT 5
        """,
    )

    run_sparql(
        graph,
        "Actions classified as severe violations",
        """
        SELECT ?action WHERE {
          ?action rdf:type legal:SevereViolation .
        }
        LIMIT 5
        """,
    )


if __name__ == "__main__":
    main()
