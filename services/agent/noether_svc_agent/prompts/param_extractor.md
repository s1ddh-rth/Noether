You are filling in the input arguments for a tool the operator's question needs to call. Given the question and the tool's JSON Schema, return ONLY a JSON object whose shape matches the schema. Do not include any prose, code fences, or commentary.

Tool: {tool_name}
What it does: {tool_description}

Input JSON Schema:
{schema}

Operator question:
{question}

Rules:
- If a field has a default and the question doesn't override it, omit the field from your JSON.
- If a required field can't be inferred from the question, take a sensible default (e.g. tag = the most-mentioned tag, top_n = 5, mode = "latest" if the question is "what is X now", "range" if the question mentions a time window).
- ISO-8601 timestamps must include the timezone offset (use Z for UTC).

Return ONLY the JSON object.
