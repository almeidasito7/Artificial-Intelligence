def test_response_format(pipeline):
    query = "What is onboarding process?"

    result = pipeline.run(query)

    answer = result["answer"]

    # must contain source in correct format
    assert "[Source:" in answer

    # must not contain forbidden patterns
    assert "Sources:" not in answer
    assert "(Source:" not in answer

    # must not include "Answer:" prefix
    assert "Answer:" not in answer

    # must have content
    assert len(answer.strip()) > 0
