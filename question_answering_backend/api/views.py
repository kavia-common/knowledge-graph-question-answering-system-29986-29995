from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import AskRequestSerializer, AskResponseSerializer
from .services import qa_service


@api_view(['GET'])
def health(request):
    """
    Health check endpoint.

    Returns 200 and a simple JSON message.
    """
    return Response({"message": "Server is up!"})


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_id='ask_question',
    operation_summary='Ask Question',
    operation_description=(
        "Submit a natural-language question to query the Neo4j-backed knowledge graph.\n\n"
        "Ocean Professional styling: expect clean responses with clear fields. "
        "Examples:\n"
        "- Who works at Contoso?\n"
        "- Where is Alice located?\n"
        "- List people in Contoso\n"
        "- What organizations is Alice affiliated with?\n"
    ),
    request_body=AskRequestSerializer,
    responses={
        200: openapi.Response(
            description="Answer payload with results, the generated Cypher query, and parameters.",
            schema=AskResponseSerializer
        ),
        400: "Invalid request",
        500: "Server error",
    },
    tags=["Question Answering"],
)
@api_view(['POST'])
def ask(request):
    """
    Ask endpoint.

    Parameters (JSON body):
    - question: string. Natural language question.
    - top_k: integer (optional). Max number of results, default 10.

    Returns:
    - question: The original question
    - cypher: The generated Cypher query (or empty if unmapped)
    - parameters: Cypher parameters used
    - results: List of result rows (dictionaries)
    - meta: Additional metadata and theme tokens
    """
    serializer = AskRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        service_payload = qa_service.ask(question=data["question"], top_k=data.get("top_k", 10))
        response_payload = AskResponseSerializer.from_payload(service_payload)
        return Response(response_payload, status=status.HTTP_200_OK)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
