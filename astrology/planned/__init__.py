"""Planned consultation: intent -> calculation plan -> engine -> retrieval from results -> brief -> writer -> fact check.

The model labels the question and writes the interpretation. It never chooses tools, never calculates and
never decides whether a rule applies. See ``consultation.py`` for the flow.
"""
