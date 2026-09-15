"""RAGAS evaluation: offline scoring of the agent's answers against a
small labeled test set.

Unlike everything else in this project, this isn't meant to run per
request -- it's a script you run after a change (a new prompt, a
different chunk size, a model swap) to check whether the agent's answers
got better or worse, against a fixed set of questions with known-good
answers.

Dependency note: ragas 0.4.3 still imports
langchain_community.chat_models.vertexai, which no longer exists in the
latest langchain-community (0.4.2) -- that module was removed as part of
langchain-community's ongoing sunset in favor of standalone integration
packages. pyproject.toml pins langchain-community==0.3.31, the last
version where that import still resolves. Remove the pin once a ragas
release fixes this upstream.

Metric note: this uses ragas.metrics' classic API (Faithfulness,
ContextPrecision, ContextRecall) with evaluate(), not the newer
ragas.metrics.collections API ragas 0.4.3 nudges you toward via a
deprecation warning. The classic API is still fully functional in this
release ("removed in v1.0", not removed now) and is what evaluate()
itself expects; the collections API uses a different LLM-wrapping
mechanism (instructor-based) that's a bigger, separate migration to take
on deliberately later, not something to half-adopt here.
AnswerRelevancy is deliberately excluded -- it needs an embeddings model,
not just an LLM judge, which is one more wrapper to wire up for one more
metric; the three included here already cover grounding (faithfulness),
ranking (context_precision), and coverage (context_recall).
"""

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import ContextPrecision, ContextRecall, Faithfulness

from src.agent.graph import agent_graph
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_RECURSION_LIMIT = 10


@dataclass
class EvalCase:
    """One labeled test question.

    reference is the known-good answer. context_recall uses it to judge
    whether the retrieved evidence actually contained what was needed --
    it's compared against the retrieved contexts, not against the agent's
    generated answer.
    """

    question: str
    reference: str


def _run_agent(question: str) -> tuple[str, list[str]]:
    """Run one question through the agent; return its answer and the
    retrieved contexts it actually used.

    Contexts are pulled from ToolMessages in the resulting message trace
    -- the literal text search_documents/search_graph returned -- rather
    than calling retrieval separately, so evaluation measures what the
    agent actually saw and reasoned over, not what retrieval could have
    returned in isolation.
    """
    result = agent_graph.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": _RECURSION_LIMIT},
    )
    messages = result["messages"]
    answer = messages[-1].content
    contexts = [m.content for m in messages if isinstance(m, ToolMessage)]
    return answer, contexts


def evaluate_cases(cases: list[EvalCase]):
    """Run every case through the agent and score the results with RAGAS."""
    samples = []
    for case in cases:
        answer, contexts = _run_agent(case.question)
        samples.append(
            SingleTurnSample(
                user_input=case.question,
                response=answer,
                retrieved_contexts=contexts or [""],  # ragas requires non-empty
                reference=case.reference,
            )
        )
        logger.info(
            "Ran case %r -> %d context(s) retrieved", case.question, len(contexts)
        )

    dataset = EvaluationDataset(samples=samples)

    judge_llm = LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL_NAME,
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_REGION,
            temperature=0.0,
        )
    )

    return evaluate(
        dataset,
        metrics=[Faithfulness(), ContextPrecision(), ContextRecall()],
        llm=judge_llm,
    )


if __name__ == "__main__":
    sample_cases = [
        EvalCase(
            question="Where does Alice work?",
            reference="Alice works at Acme Corp.",
        ),
        EvalCase(
            question="Who does Alice report to?",
            reference="Alice reports to Bob.",
        ),
    ]
    result = evaluate_cases(sample_cases)
    print(result)