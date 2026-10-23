
from pipeline import extract_requirements

jd = """
Role: AI/ML Intern
Required skills: Python, machine learning, model evaluation.
Preferred skills: FastAPI and SQL.
"""

resume = """
Built a Python classification project.
Used logistic regression and evaluated it using F1-score.
Created a small FastAPI endpoint for predictions.
"""

result = extract_requirements(jd, resume)
import json
print(json.dumps(result, indent=2))