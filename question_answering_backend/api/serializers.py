from typing import Any, Dict
from rest_framework import serializers


# PUBLIC_INTERFACE
class AskRequestSerializer(serializers.Serializer):
    """
    Serializer for incoming question requests.
    """
    question = serializers.CharField(
        help_text="A natural language question to query the knowledge graph.",
        allow_blank=False,
        trim_whitespace=True,
        max_length=500,
    )
    top_k = serializers.IntegerField(
        help_text="Optional limit on number of results.",
        required=False,
        min_value=1,
        max_value=100,
        default=10,
    )


# PUBLIC_INTERFACE
class AskResponseSerializer(serializers.Serializer):
    """
    Serializer for outgoing answers. Includes raw Cypher, parameters and results.
    """
    question = serializers.CharField()
    cypher = serializers.CharField()
    parameters = serializers.DictField(child=serializers.CharField(), required=False)
    results = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    meta = serializers.DictField(required=False)

    @staticmethod
    def from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to coerce payload into serializer-validated dict.
        """
        return {
            "question": payload.get("question", ""),
            "cypher": payload.get("cypher", ""),
            "parameters": payload.get("parameters", {}) or {},
            "results": payload.get("results", []) or [],
            "meta": payload.get("meta", {}) or {},
        }
