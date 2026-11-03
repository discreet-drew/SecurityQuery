from __future__ import annotations
from secquery.llm import OllamaClient


def answer_without_retrieval(question: str, llm: OllamaClient) -> str:
    prompt = (
        "You are an evaluation baseline. Answer this cybersecurity question from model knowledge only. "
        "Do not claim to have checked any documents or live system. Mention uncertainty. "
        "This answer is not evidence-grounded and must not be presented as verified guidance.\n"
        f"Question: {question}"
    )
    return llm.generate(prompt)
