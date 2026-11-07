"""Every outside source we use, in one place, so the /sources page and the write-up cannot drift apart.

Only list a source here if the app really uses it. Add one when a feature starts depending on it.
"""

SOURCES = [
    {"name": "PKDD'99 Discovery Challenge Financial dataset (real, anonymized bank data)",
     "url": "https://relational.fel.cvut.cz/dataset/Financial",
     "publisher": "CTU Prague Relational Dataset Repository",
     "used_for": "All account, transaction, loan and monthly-summary numbers (via the Tangerine datathon data pack)."},
    {"name": "Employment Insurance regular benefits",
     "url": "https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit.html",
     "publisher": "Government of Canada",
     "used_for": "The 55% income figure behind the job-loss (EI) preset in the Shock Lab."},
    {"name": "Gemini API (Google)",
     "url": "https://ai.google.dev/",
     "publisher": "Google",
     "used_for": "Turning a twist card typed in plain English into shock settings, and reading unfamiliar "
                 "statement layouts. Only card text or masked statement text is sent; no dataset rows."},
]
