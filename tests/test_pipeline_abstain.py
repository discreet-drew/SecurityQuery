from secquery.pipeline import SecQuery

def test_pipeline_abstains_when_no_documents_are_indexed(test_settings, fake_embedder, fake_llm):
    engine = SecQuery(test_settings, embedder=fake_embedder, llm=fake_llm)
    result = engine.ask("Is my company server compromised right now?")
    assert result.abstained
    assert result.reason
    assert fake_llm.json_calls == 0


def test_pipeline_empty_question_is_handled(test_settings, fake_embedder, fake_llm):
    engine = SecQuery(test_settings, embedder=fake_embedder, llm=fake_llm)
    result = engine.ask("   ")
    assert result.abstained
    assert "enter a question" in result.answer.lower()


def test_pipeline_returns_only_verified_claims(test_settings, fake_embedder, make_pdf, tmp_path):
    from conftest import FakeLLM

    quote = "Upgrade to version 4.2.8."
    llm = FakeLLM({
        "answer": "The fixed version is 4.2.8.",
        "claims": [{
            "text": "The document recommends upgrading to 4.2.8.",
            "quote": quote,
            "document_id": "",
            "document_name": "",
            "page_number": 1,
        }],
        "abstain": False,
        "reason": "",
    })
    engine = SecQuery(test_settings, embedder=fake_embedder, llm=llm)
    pdf = make_pdf(tmp_path / "advisory.pdf", [quote])
    engine.add_document(pdf, trust_level="synthetic")
    result = engine.ask("What fixed version does the document state?")
    assert not result.abstained
    assert len(result.claims) == 1
    assert result.claims[0].verified
    assert "p. 1" in result.answer


def test_vector_only_baseline_is_separately_callable(test_settings, fake_embedder, fake_llm):
    engine = SecQuery(test_settings, embedder=fake_embedder, llm=fake_llm)
    result = engine.ask_vector_only("What fixed version does the document state?")
    assert result.abstained
    assert result.reason
