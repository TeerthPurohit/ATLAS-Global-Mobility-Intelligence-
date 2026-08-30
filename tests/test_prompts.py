"""Phase 4 prompt-versioning tests: each rag/prompts/*.py module exposes a
real TEMPLATE + VERSION, the two templated ones still .format() with their
real kwargs, and each original caller module's constant equals the
imported one (catches copy-paste drift during the move to rag/prompts/).
"""
import sys
from pathlib import Path

RAG_DIR = Path(__file__).resolve().parents[1] / "rag"
sys.path.insert(0, str(RAG_DIR))
sys.path.insert(0, str(RAG_DIR / "insight_generation"))
sys.path.insert(0, str(RAG_DIR / "nl_to_sql"))
sys.path.insert(0, str(RAG_DIR / "router"))

from prompts import classifier_prompt, insight_doc_prompt, journey_narrative_prompt, sql_agent_prompt, synthesis_prompt

import generate_insight_docs
import journey_narrative
import query_classifier
import rag_pipeline
import sql_agent

_PROMPT_MODULES = [classifier_prompt, sql_agent_prompt, insight_doc_prompt, synthesis_prompt, journey_narrative_prompt]


def test_every_prompt_module_has_version_and_template():
    for mod in _PROMPT_MODULES:
        assert isinstance(mod.VERSION, str) and mod.VERSION, f"{mod.__name__} missing a non-empty VERSION"
        assert isinstance(mod.TEMPLATE, str) and mod.TEMPLATE.strip(), f"{mod.__name__} missing a non-empty TEMPLATE"


def test_sql_agent_prompt_formats_with_real_kwargs():
    rendered = sql_agent_prompt.TEMPLATE.format(city_name="NYC", schema="fake schema text")
    assert "NYC" in rendered
    assert "fake schema text" in rendered


def test_synthesis_prompt_formats_with_real_kwargs():
    rendered = synthesis_prompt.TEMPLATE.format(context="some retrieved context")
    assert "some retrieved context" in rendered


def test_caller_modules_import_the_same_prompt_text():
    assert query_classifier.SYSTEM_PROMPT == classifier_prompt.TEMPLATE
    assert query_classifier.PROMPT_VERSION == classifier_prompt.VERSION

    assert sql_agent.SYSTEM_PROMPT_TEMPLATE == sql_agent_prompt.TEMPLATE
    assert sql_agent.PROMPT_VERSION == sql_agent_prompt.VERSION

    assert generate_insight_docs.SYSTEM_PROMPT == insight_doc_prompt.TEMPLATE
    assert generate_insight_docs.PROMPT_VERSION == insight_doc_prompt.VERSION

    assert rag_pipeline.SYNTHESIS_SYSTEM_PROMPT == synthesis_prompt.TEMPLATE
    assert rag_pipeline.SYNTHESIS_PROMPT_VERSION == synthesis_prompt.VERSION

    assert journey_narrative.SYSTEM_PROMPT == journey_narrative_prompt.TEMPLATE
    assert journey_narrative.PROMPT_VERSION == journey_narrative_prompt.VERSION
