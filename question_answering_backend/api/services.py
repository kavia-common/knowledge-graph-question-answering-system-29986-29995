"""
Application services that orchestrate NLP mapping and Neo4j querying.
"""
from typing import Any, Dict, List

from .nlp_mapping import RuleBasedNLPMappings
from .neo4j_service import neo4j_service


class QuestionAnswerService:
    """
    Orchestrates the flow:
    - Take a natural language question
    - Map to Cypher via simple rules
    - Execute Cypher via Neo4j service
    - Return results with metadata
    """

    def __init__(self) -> None:
        self._mapper = RuleBasedNLPMappings()

    # PUBLIC_INTERFACE
    def ask(self, question: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Process the question and return structured results.

        Returns:
            Dict containing: question, cypher, parameters, results, meta
        """
        mapping = self._mapper.map_question(question, top_k=top_k)
        if not mapping:
            return {
                "question": question,
                "cypher": "",
                "parameters": {},
                "results": [],
                "meta": {
                    "note": "No mapping found. Try a supported pattern like 'Who works at OrgName?'",
                    "supported_examples": [
                        "Who works at Contoso?",
                        "Where is Alice located?",
                        "List people in Contoso",
                        "What organizations is Alice affiliated with?",
                        "Who is Alice?"
                    ],
                },
            }

        rows: List[Dict[str, Any]] = neo4j_service.run_cypher(mapping.query, mapping.parameters)
        return {
            "question": question,
            "cypher": mapping.query,
            "parameters": mapping.parameters,
            "results": rows,
            "meta": {
                "theme": {
                    "name": "Ocean Professional",
                    "primary": "#2563EB",
                    "secondary": "#F59E0B",
                    "success": "#F59E0B",
                    "error": "#EF4444",
                }
            },
        }


qa_service = QuestionAnswerService()
