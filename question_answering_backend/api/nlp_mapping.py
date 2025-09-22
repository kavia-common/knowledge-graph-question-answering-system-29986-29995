"""
Beginner-friendly NLP mapping utilities that convert simple natural language
questions into Cypher queries.

This module intentionally keeps logic straightforward and well-documented so it
can act as a teaching reference. You can extend RuleBasedNLPMappings with more
patterns over time.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CypherQuery:
    """
    Represents a Cypher query and associated parameters.
    """
    query: str
    parameters: Dict


class RuleBasedNLPMappings:
    """
    A tiny rules engine for mapping specific natural language patterns to Cypher.
    For production, consider using a proper NLP pipeline and entity extraction.

    Current supported patterns (case-insensitive):
    - "who works at {organization}?"
    - "where is {person} located?"
    - "list people in {organization}"
    - "what organizations is {person} affiliated with?"
    """

    def map_question(self, question: str, top_k: int = 10) -> Optional[CypherQuery]:
        """
        Map a question to a CypherQuery if a supported rule matches.

        Args:
            question: Natural language question.
            top_k: Limit for results.

        Returns:
            CypherQuery if a rule matched, otherwise None.
        """
        if not question:
            return None

        q = question.strip().lower()

        # Pattern: who works at {organization}
        if q.startswith("who works at "):
            org = q.replace("who works at ", "", 1).rstrip("?").strip()
            if org:
                return CypherQuery(
                    query=(
                        "MATCH (p:Person)-[:WORKS_AT]->(o:Organization {name: $org}) "
                        "RETURN p.name AS person LIMIT $top_k"
                    ),
                    parameters={"org": org, "top_k": top_k},
                )

        # Pattern: where is {person} located
        if q.startswith("where is ") and q.endswith(" located?"):
            person = q[len("where is "):-len(" located?")].strip()
            if person:
                return CypherQuery(
                    query=(
                        "MATCH (p:Person {name: $person})-[:LOCATED_IN]->(l:Location) "
                        "RETURN l.name AS location LIMIT $top_k"
                    ),
                    parameters={"person": person, "top_k": top_k},
                )

        # Pattern: list people in {organization}
        if q.startswith("list people in "):
            org = q.replace("list people in ", "", 1).rstrip("?").strip()
            if org:
                return CypherQuery(
                    query=(
                        "MATCH (o:Organization {name: $org})<-[:WORKS_AT]-(p:Person) "
                        "RETURN p.name AS person ORDER BY p.name LIMIT $top_k"
                    ),
                    parameters={"org": org, "top_k": top_k},
                )

        # Pattern: what organizations is {person} affiliated with
        if q.startswith("what organizations is ") and q.endswith(" affiliated with?"):
            person = q.replace("what organizations is ", "", 1).replace(" affiliated with?", "", 1).strip()
            if person:
                return CypherQuery(
                    query=(
                        "MATCH (p:Person {name: $person})-[:WORKS_AT]->(o:Organization) "
                        "RETURN o.name AS organization ORDER BY o.name LIMIT $top_k"
                    ),
                    parameters={"person": person, "top_k": top_k},
                )

        # Fallback: try a basic generic person by name lookup
        if q.startswith("who is "):
            person = q.replace("who is ", "", 1).rstrip("?").strip()
            if person:
                return CypherQuery(
                    query=(
                        "MATCH (p:Person {name: $person}) "
                        "OPTIONAL MATCH (p)-[:WORKS_AT]->(o:Organization) "
                        "OPTIONAL MATCH (p)-[:LOCATED_IN]->(l:Location) "
                        "RETURN p.name AS person, o.name AS organization, l.name AS location "
                        "LIMIT $top_k"
                    ),
                    parameters={"person": person, "top_k": top_k},
                )

        return None
