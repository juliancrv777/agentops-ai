from uuid import uuid4

from app.routers.chat import extractive_answer
from app.schemas import ChatCitation


def test_extractive_answer_is_explicitly_not_a_model_response() -> None:
    citation = ChatCitation(
        document_id=uuid4(), chunk_id=uuid4(), filename="guide.md",
        score=0.76, excerpt="Restart workers only after verifying queues.",
    )
    answer = extractive_answer([citation])
    assert "not an AI-generated answer" in answer
    assert "guide.md" in answer
    assert "Restart workers" in answer


def test_extractive_answer_without_evidence() -> None:
    assert "No relevant documents" in extractive_answer([])
