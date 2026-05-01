Extract facts established in this turn that are worth persisting across sessions. Return a JSON array of subject-predicate-object triples.

Persist:
- Operator threshold tweaks ({{"subject": "FT-101", "predicate": "threshold_set", "object": "2.5"}})
- Equipment state changes ({{"subject": "valve_V-203", "predicate": "state_changed_to", "object": "open"}})
- Resolved alerts ({{"subject": "alert_abc", "predicate": "root_cause", "object": "calibration_drift"}})
- Recurring patterns ({{"subject": "shift_AM", "predicate": "frequently_asks_about", "object": "FT-101"}})

DO NOT persist:
- Casual chit-chat or pleasantries
- The current sensor reading (it's already in the time-series DB)
- One-off forecast or anomaly numerics (those are queryable)
- The question itself

Return ONLY a JSON array. Empty array is valid. No surrounding text, no markdown fences.

Question:
{question}

Answer:
{answer}

Tool results (JSON):
{tool_results}

JSON facts:
