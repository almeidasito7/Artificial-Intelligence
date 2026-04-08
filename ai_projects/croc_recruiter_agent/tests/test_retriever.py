def test_retriever_returns_results():
    from src.rag.retriever import Retriever

    retriever = Retriever()

    results = retriever.retrieve("What is onboarding process?")

    assert isinstance(results, list)
    assert len(results) > 0

    first = results[0]

    assert "text" in first
    assert "score" in first
    assert "source" in first