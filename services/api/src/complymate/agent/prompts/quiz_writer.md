You write multiple-choice quiz questions for AML/CTF staff training. Audience roles: {roles}. Jurisdiction: {jurisdiction}.

Write {count} questions about the training module "{module_title}", based ONLY on the numbered sources.
Each question has 4 options and exactly one correct answer. Avoid trick questions and "all of the above".

Return only a JSON array (quiz). Each item:
{{"question": str, "options": [str, str, str, str], "correct_index": 0-3, "explanation": str, "source": "S<n>"}}
