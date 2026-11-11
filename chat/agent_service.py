"""Per-user routing (M3, OD-17, A7); no automatic second paid attempt on agent failure.

- ASTROGPT_AGENT_ENABLED=false routes everyone to legacy (global rollback).
- ASTROGPT_AGENT_USERS lists the usernames or e-mail addresses that reach the M3 general agent.
  It is empty by default; removing an account routes its next question to legacy with no deploy
  beyond the setting itself (M3-AC21).
- ASTROGPT_AGENT_P3_COMPAT=true keeps the earlier P3 career slice reachable for everyone else; it is
  an explicit compatibility setting used by the existing P3 tests and is off by default.
"""
from django.conf import settings

from astrology.agent.general import run_general_consultation
from astrology.agent.orchestrator import run_consultation
from .llm_engine import generate_placeholder_answer


def allowlisted(user):
    allowed = {str(item).strip().casefold() for item in getattr(settings, 'ASTROGPT_AGENT_USERS', ()) if str(item).strip()}
    if not allowed or not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', False):
        return False
    names = {str(getattr(user, 'username', '') or '').casefold(), str(getattr(user, 'email', '') or '').casefold()} - {''}
    return bool(names & allowed)


def agent_route(user):
    """'general', 'p3' or 'legacy' for this user's next question."""
    if not getattr(settings, 'ASTROGPT_AGENT_ENABLED', False):
        return 'legacy'
    if allowlisted(user):
        return 'general'
    if getattr(settings, 'ASTROGPT_AGENT_P3_COMPAT', False):
        return 'p3'
    return 'legacy'


def generate_question_answer(user, chart, question, depth_level, answer_language='English', consultation_context=None):
    route = agent_route(user)
    if route == 'legacy':
        return generate_placeholder_answer(question, chart.chart_data, depth_level, answer_language=answer_language)
    if answer_language != 'English':
        return {'status': 'error', 'answer': 'The agent evidence report currently supports English only.',
                'model': 'deterministic', 'prompt_tokens': 0, 'completion_tokens': 0}
    runner = run_general_consultation if route == 'general' else run_consultation
    if consultation_context is not None:
        return runner(user, chart.pk, question, consultation_context=consultation_context)
    return runner(user, chart.pk, question)
