from __future__ import annotations

from typing import Dict, List, Set, Tuple

from app.domains.extraction.schemas import ExtractedRelation


class FamilyJsonBuilder:
    """
    Convert extracted relations into a graph JSON structure for visualization.

    Input:
        List[ExtractedRelation]

    Output:
        {
            "people": [...],
            "relationships": [...]
        }
    """

    def build(self, relations: List[ExtractedRelation]) -> dict:
        people_map: Dict[str, dict] = {}
        relationships: List[dict] = []
        seen_relationships: Set[Tuple[str, str, str]] = set()

        for relation in relations:
            source_name = self._clean_name(relation.source_person)
            target_name = self._clean_name(relation.target_person)

            if not source_name or not target_name:
                continue

            source_id = self._get_or_create_person_id(
                name=source_name,
                people_map=people_map,
            )
            target_id = self._get_or_create_person_id(
                name=target_name,
                people_map=people_map,
            )

            relation_key = self._make_relationship_key(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation.relation_type,
            )

            if relation_key in seen_relationships:
                continue

            seen_relationships.add(relation_key)

            relationship_id = f"R{len(relationships) + 1:03d}"

            relationships.append(
                {
                    "id": relationship_id,
                    "from_id": source_id,
                    "from_name": source_name,
                    "to_id": target_id,
                    "to_name": target_name,
                    "type": relation.relation_type,
                    "confidence": relation.confidence,
                    "evidence": relation.evidence,
                    "rule_name": relation.rule_name,
                }
            )

        return {
            "people": list(people_map.values()),
            "relationships": relationships,
        }

    def _get_or_create_person_id(
        self,
        name: str,
        people_map: Dict[str, dict],
    ) -> str:
        if name not in people_map:
            person_id = f"P{len(people_map) + 1:03d}"

            people_map[name] = {
                "id": person_id,
                "full_name": name,
            }

        return people_map[name]["id"]

    def _make_relationship_key(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
    ) -> Tuple[str, str, str]:
        """
        spouse_of is bidirectional, so:
            A spouse_of B
            B spouse_of A

        should be saved only once in graph JSON.

        parent_of is directional, so:
            A parent_of B
        is different from:
            B parent_of A
        """

        if relation_type == "spouse_of":
            person_1, person_2 = sorted([source_id, target_id])
            return relation_type, person_1, person_2

        return relation_type, source_id, target_id

    def _clean_name(self, name: str) -> str:
        return " ".join(name.strip().split())