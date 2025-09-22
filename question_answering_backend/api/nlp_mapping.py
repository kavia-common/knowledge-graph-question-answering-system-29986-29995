"""
Beginner-friendly NLP mapping utilities that convert simple natural language
questions into Cypher queries.

This module intentionally keeps logic straightforward and well-documented so it
can act as a teaching reference. You can extend RuleBasedNLPMappings with more
patterns over time.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List


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
    - "who works at <organization>?"
    - "where is <person> located?"
    - "list people in <organization>"
    - "what organizations is <person> affiliated with?"
    - "who is the coach of <person>?" / "who coached <person>?"

    Sachin-specific examples supported (case-insensitive):
    - "what teams did sachin tendulkar play for?"
      Example Cypher:
        MATCH (p:Person)-[:PLAYED_FOR|:REPRESENTED|:CAPTAINED]->(t)
        WHERE toLower(p.name) CONTAINS toLower($person)
           OR toLower(coalesce(p.full_name, '')) CONTAINS toLower($person)
           OR toLower(coalesce(p.nickname, '')) CONTAINS toLower($person)
        RETURN DISTINCT t.name AS team
        LIMIT $TOP_K
    - "what records does sachin tendulkar hold?"
      Example Cypher:
        MATCH (p:Person)-[:HOLDS_RECORD]->(r:Record)
        WHERE toLower(p.name) CONTAINS toLower($person)
           OR toLower(coalesce(p.full_name, '')) CONTAINS toLower($person)
           OR toLower(coalesce(p.nickname, '')) CONTAINS toLower($person)
        RETURN r.label AS record, r.value AS value, r.unit AS unit, r.year AS year
        LIMIT $TOP_K
    - "when did sachin tendulkar debut in odi/test/international cricket?"
      Example Cypher (format-aware):
        MATCH (p:Person)-[:DEBUTED_IN]->(d:Record {type:'Debut'})
        WHERE (toLower(p.name) CONTAINS toLower($person)
           OR toLower(coalesce(p.full_name, '')) CONTAINS toLower($person)
           OR toLower(coalesce(p.nickname, '')) CONTAINS toLower($person))
          AND (($format IS NULL) OR toLower(d.format) = toLower($format))
        RETURN d.format AS format, d.year AS year, d.opponent AS opponent, d.location AS location
        ORDER BY d.year ASC
        LIMIT $TOP_K
    - "when did sachin tendulkar retire?"
      Example Cypher:
        MATCH (p:Person)-[:RETIRED_IN]->(r:Record {type:'Retirement'})
        WHERE toLower(p.name) CONTAINS toLower($person)
           OR toLower(coalesce(p.full_name, '')) CONTAINS toLower($person)
           OR toLower(coalesce(p.nickname, '')) CONTAINS toLower($person)
        RETURN r.format AS format, r.year AS year, r.opponent AS opponent, r.location AS location
        ORDER BY r.year ASC
        LIMIT $TOP_K
    - "what are the career statistics of sachin tendulkar in odi/test/international?"
      Example Cypher (format-aware):
        MATCH (p:Person)-[:FORMAT_STATS]->(s:Record {type:'Stats'})
        WHERE (toLower(p.name) CONTAINS toLower($person)
           OR toLower(coalesce(p.full_name, '')) CONTAINS toLower($person)
           OR toLower(coalesce(p.nickname, '')) CONTAINS toLower($person))
          AND (($format IS NULL) OR toLower(s.format) = toLower($format))
        RETURN s.format AS format, s.matches AS matches, s.runs AS runs, s.hundreds AS hundreds, s.fifties AS fifties, s.average AS average
        ORDER BY s.format
        LIMIT $TOP_K
    - "where was sachin tendulkar born?"
      Example Cypher:
        MATCH (p:Person)-[:BORN_IN]->(c:City)
        WHERE toLower(p.name) CONTAINS toLower($person)
           OR toLower(coalesce(p.full_name, '')) CONTAINS toLower($person)
           OR toLower(coalesce(p.nickname, '')) CONTAINS toLower($person)
        OPTIONAL MATCH (c)-[:IN_COUNTRY]->(country:Country)
        RETURN c.name AS city, country.name AS country
        LIMIT $TOP_K
    - "tell me about sachin tendulkar"
      Example Cypher (general info summary):
        MATCH (p:Person)
        WHERE toLower(p.name) CONTAINS toLower($person)
           OR toLower(coalesce(p.full_name, '')) CONTAINS toLower($person)
           OR toLower(coalesce(p.nickname, '')) CONTAINS toLower($person)
        OPTIONAL MATCH (p)-[:BORN_IN]->(city:City)
        OPTIONAL MATCH (p)-[:FORMAT_STATS]->(s:Record {type:'Stats'})
        RETURN p.name AS name, p.full_name AS full_name, p.nickname AS nickname, p.batting_style AS batting_style,
               p.bowling_style AS bowling_style, p.birth_year AS birth_year,
               city.name AS birth_city, collect({format:s.format, runs:s.runs, matches:s.matches}) AS formats
        LIMIT 1
    """

    def _normalize_person_input(self, person: str) -> List[str]:
        """
        Normalize a user-supplied person name into a list of possible aliases to try.
        Includes:
        - Raw form
        - Stripped of periods (e.g., 'S. Tendulkar' -> 'S Tendulkar')
        - Simple initial expansion if it looks like 'X. Lastname' -> ['X Lastname', 'Sachin Tendulkar'] for demo

        Note: This is a light heuristic. In production, alias expansion would come from the KG or an alias table.
        """
        p = (person or "").strip()
        if not p:
            return []
        variants = {p, p.replace(".", "").strip()}

        # Demo-focused: If looks like 'S Tendulkar' or 'S. Tendulkar', add 'Sachin Tendulkar'
        tokens = p.replace(".", "").split()
        if len(tokens) == 2 and len(tokens[0]) == 1 and tokens[1].lower() == "tendulkar":
            variants.add("Sachin Tendulkar")

        return [v for v in variants if v]

    def _person_where_clause(self, field: str = "p") -> str:
        """
        Build a reusable Cypher WHERE clause that matches Person by:
        - case-insensitive exact name
        - case-insensitive substring (CONTAINS)
        - matching against common alias properties if present (full_name, nickname)

        Usage: ... MATCH (p:Person) WHERE <clause> ...
        It expects parameters:
          $person OR $persons (list)
        """
        # We support a single $person OR a list $persons; if list present we OR across them.
        # Using coalesce toLower to avoid null issues for optional properties.
        # Any of the properties matching is accepted.
        # Use COALESCE to avoid unbound parameter errors if either is missing.
        single_pred = (
            "("
            " toLower({f}.name) CONTAINS toLower(coalesce($person, '')) OR "
            " toLower(coalesce({f}.full_name, '')) CONTAINS toLower(coalesce($person, '')) OR "
            " toLower(coalesce({f}.nickname, '')) CONTAINS toLower(coalesce($person, '')) "
            ")"
        ).format(f=field)

        list_pred = (
            "("
            " ANY(personParam IN coalesce($persons, []) WHERE "
            "   toLower({f}.name) CONTAINS toLower(personParam) OR "
            "   toLower(coalesce({f}.full_name, '')) CONTAINS toLower(personParam) OR "
            "   toLower(coalesce({f}.nickname, '')) CONTAINS toLower(personParam)"
            " )"
            ")"
        ).format(f=field)

        # Include both; with COALESCE this is safe if one is absent.
        return f"(({list_pred}) OR ({single_pred}))"

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

        # -------------------------
        # Generic demo rules (existing)
        # -------------------------

        # Pattern: who works at <organization>
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

        # Pattern: where is <person> located
        if q.startswith("where is ") and q.endswith(" located?"):
            person = q[len("where is "):-len(" located?")].strip()
            if person:
                persons = self._normalize_person_input(person)
                params = {"top_k": top_k}
                if len(persons) > 1:
                    params["persons"] = persons
                else:
                    params["person"] = persons[0] if persons else person
                return CypherQuery(
                    query=(
                        "MATCH (p:Person)-[:LOCATED_IN]->(l:Location) "
                        f"WHERE {self._person_where_clause('p')} "
                        "RETURN l.name AS location LIMIT $top_k"
                    ),
                    parameters=params,
                )

        # Pattern: list people in <organization>
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

        # Pattern: what organizations is <person> affiliated with
        if q.startswith("what organizations is ") and q.endswith(" affiliated with?"):
            person = q.replace("what organizations is ", "", 1).replace(" affiliated with?", "", 1).strip()
            if person:
                persons = self._normalize_person_input(person)
                params = {"top_k": top_k}
                if len(persons) > 1:
                    params["persons"] = persons
                else:
                    params["person"] = persons[0] if persons else person
                return CypherQuery(
                    query=(
                        "MATCH (p:Person)-[:WORKS_AT]->(o:Organization) "
                        f"WHERE {self._person_where_clause('p')} "
                        "RETURN o.name AS organization ORDER BY o.name LIMIT $top_k"
                    ),
                    parameters=params,
                )

        # Pattern: who is the coach of <person> / who coached <person>
        # Supports: "who is the coach of sachin tendulkar?", "who coached sachin tendulkar?"
        if q.startswith("who is the coach of ") or q.startswith("who coached "):
            person = (
                q.replace("who is the coach of ", "", 1)
                 .replace("who coached ", "", 1)
                 .rstrip("?")
                 .strip()
            )
            if person:
                persons = self._normalize_person_input(person)
                params = {"top_k": top_k}
                if len(persons) > 1:
                    params["persons"] = persons
                else:
                    params["person"] = persons[0] if persons else person
                # We support both relationship directions for robustness:
                # (coach)-[:COACHED]->(student) and (student)-[:COACHED_BY]->(coach)
                return CypherQuery(
                    query=(
                        "MATCH (p:Person) "
                        f"WHERE {self._person_where_clause('p')} "
                        "OPTIONAL MATCH (c1:Person)-[:COACHED]->(p) "
                        "OPTIONAL MATCH (p)-[:COACHED_BY]->(c2:Person) "
                        "WITH p, coalesce(c1, c2) AS coach "
                        "WHERE coach IS NOT NULL "
                        "RETURN DISTINCT coach.name AS coach "
                        "LIMIT $top_k"
                    ),
                    parameters=params,
                )

        # Fallback: try a basic generic person by name lookup
        if q.startswith("who is "):
            person = q.replace("who is ", "", 1).rstrip("?").strip()
            if person:
                persons = self._normalize_person_input(person)
                params = {"top_k": top_k}
                if len(persons) > 1:
                    params["persons"] = persons
                else:
                    params["person"] = persons[0] if persons else person
                return CypherQuery(
                    query=(
                        "MATCH (p:Person) "
                        f"WHERE {self._person_where_clause('p')} "
                        "OPTIONAL MATCH (p)-[:WORKS_AT]->(o:Organization) "
                        "OPTIONAL MATCH (p)-[:LOCATED_IN]->(l:Location) "
                        "RETURN p.name AS person, o.name AS organization, l.name AS location "
                        "LIMIT $top_k"
                    ),
                    parameters=params,
                )

        # -------------------------
        # Sachin Tendulkar specific rules
        # -------------------------

        # Normalize helpful constants
        SACHIN = "sachin tendulkar"

        # 1) What teams did Sachin Tendulkar play for?
        # Supports: "what teams did sachin tendulkar play for?" and close variants
        if ("what teams did" in q and "sachin tendulkar" in q and "play for" in q) or \
           q.strip() == "teams sachin tendulkar played for?":
            return CypherQuery(
                query=(
                    "MATCH (p:Person)-[:PLAYED_FOR|:REPRESENTED|:CAPTAINED]->(t) "
                    f"WHERE {self._person_where_clause('p')} "
                    "RETURN DISTINCT t.name AS team "
                    "ORDER BY team "
                    "LIMIT $top_k"
                ),
                parameters={"person": "Sachin Tendulkar", "top_k": top_k},
            )

        # 2) What records does Sachin Tendulkar hold?
        if ("what records does" in q and "sachin tendulkar" in q and "hold" in q) or \
           q.strip() in {"sachin tendulkar records?", "records of sachin tendulkar?"}:
            return CypherQuery(
                query=(
                    "MATCH (p:Person)-[:HOLDS_RECORD]->(r:Record) "
                    f"WHERE {self._person_where_clause('p')} "
                    "RETURN r.label AS record, r.value AS value, r.unit AS unit, r.year AS year "
                    "ORDER BY record "
                    "LIMIT $top_k"
                ),
                parameters={"person": "Sachin Tendulkar", "top_k": top_k},
            )

        # Helper to extract a cricket format keyword if present
        def _extract_format(text: str) -> Optional[str]:
            # Recognize common format names seeded in the graph
            if "test" in text:
                return "Test"
            if "odi" in text:
                return "ODI"
            if "t20i" in text or "t20" in text:
                return "T20I"
            if "ipl" in text:
                return "IPL"
            if "international" in text:
                # If user says "international", we don't have a direct "International" Stats node in seed,
                # instead combine via multiple formats. For demo, return None to fetch all formats.
                return None
            return None

        # 3) When did Sachin Tendulkar debut in ODI/Test/International cricket?
        if ("when did" in q and "sachin tendulkar" in q and "debut" in q):
            fmt = _extract_format(q)  # None means all formats
            return CypherQuery(
                query=(
                    "MATCH (p:Person)-[:DEBUTED_IN]->(d:Record {type:'Debut'}) "
                    f"WHERE {self._person_where_clause('p')} "
                    "AND (($format IS NULL) OR toLower(d.format) = toLower($format)) "
                    "RETURN d.format AS format, d.year AS year, d.opponent AS opponent, d.location AS location "
                    "ORDER BY d.year ASC "
                    "LIMIT $top_k"
                ),
                parameters={"person": "Sachin Tendulkar", "format": fmt, "top_k": top_k},
            )

        # 4) When did Sachin Tendulkar retire?
        if ("when did" in q and "sachin tendulkar" in q and "retire" in q):
            fmt = _extract_format(q)  # Optional format filter
            return CypherQuery(
                query=(
                    "MATCH (p:Person)-[:RETIRED_IN]->(r:Record {type:'Retirement'}) "
                    f"WHERE {self._person_where_clause('p')} "
                    "AND (($format IS NULL) OR toLower(r.format) = toLower($format)) "
                    "RETURN r.format AS format, r.year AS year, r.opponent AS opponent, r.location AS location "
                    "ORDER BY r.year ASC "
                    "LIMIT $top_k"
                ),
                parameters={"person": "Sachin Tendulkar", "format": fmt, "top_k": top_k},
            )

        # 5) What are the career statistics of Sachin Tendulkar in ODI/Test/International?
        if (("what are the career statistics of" in q or "career statistics of" in q or "stats of" in q)
                and "sachin tendulkar" in q):
            fmt = _extract_format(q)
            return CypherQuery(
                query=(
                    "MATCH (p:Person)-[:FORMAT_STATS]->(s:Record {type:'Stats'}) "
                    f"WHERE {self._person_where_clause('p')} "
                    "AND (($format IS NULL) OR toLower(s.format) = toLower($format)) "
                    "RETURN s.format AS format, s.matches AS matches, s.runs AS runs, "
                    "s.hundreds AS hundreds, s.fifties AS fifties, s.average AS average "
                    "ORDER BY s.format "
                    "LIMIT $top_k"
                ),
                parameters={"person": "Sachin Tendulkar", "format": fmt, "top_k": top_k},
            )

        # 6) Where was Sachin Tendulkar born?
        if ("where was" in q and "sachin tendulkar" in q and "born" in q) or \
           q.strip() in {"sachin tendulkar birthplace?", "birthplace of sachin tendulkar?"}:
            return CypherQuery(
                query=(
                    "MATCH (p:Person)-[:BORN_IN]->(c:City) "
                    f"WHERE {self._person_where_clause('p')} "
                    "OPTIONAL MATCH (c)-[:IN_COUNTRY]->(country:Country) "
                    "RETURN c.name AS city, country.name AS country "
                    "LIMIT $top_k"
                ),
                parameters={"person": "Sachin Tendulkar", "top_k": top_k},
            )

        # 7) Tell me about Sachin Tendulkar (general info)
        if q.startswith("tell me about ") and SACHIN in q or q.strip() in {"about sachin tendulkar", "who is sachin tendulkar"}:
            return CypherQuery(
                query=(
                    "MATCH (p:Person) "
                    f"WHERE {self._person_where_clause('p')} "
                    "OPTIONAL MATCH (p)-[:BORN_IN]->(city:City) "
                    "OPTIONAL MATCH (p)-[:FORMAT_STATS]->(s:Record {type:'Stats'}) "
                    "RETURN p.name AS name, p.full_name AS full_name, p.nickname AS nickname, "
                    "p.batting_style AS batting_style, p.bowling_style AS bowling_style, "
                    "p.birth_year AS birth_year, city.name AS birth_city, "
                    "collect({format:s.format, runs:s.runs, matches:s.matches, hundreds:s.hundreds, fifties:s.fifties, average:s.average}) AS formats "
                    "LIMIT 1"
                ),
                parameters={"person": "Sachin Tendulkar"},
            )

        return None
