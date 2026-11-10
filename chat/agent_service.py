"""Feature-flag routing; no automatic second paid attempt on agent failure."""
from django.conf import settings
from astrology.agent.orchestrator import run_consultation
from .llm_engine import generate_placeholder_answer


def generate_question_answer(user, chart, question, depth_level, answer_language='English', consultation_context=None):
    if not getattr(settings, 'ASTROGPT_AGENT_ENABLED', False):
        return generate_placeholder_answer(question, chart.chart_data, depth_level, answer_language=answer_language)
    if answer_language != 'English':
        return {'status': 'error', 'answer': 'The P3 evidence report currently supports English only.',
                'model': 'deterministic', 'prompt_tokens': 0, 'completion_tokens': 0}
    if consultation_context is not None:
        return run_consultation(user, chart.pk, question, consultation_context=consultation_context)
    return run_consultation(user, chart.pk, question)
