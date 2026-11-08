"""Every outside source we use, in one place, so the /sources page and the write-up cannot drift apart.

Only list a source here if the app really uses it. Add one when a feature starts depending on it.
data/external/README.md lists the same external tables row by row.
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
    {"name": "EI regular benefits: how much you could receive (2026 maximum $729/week)",
     "url": "https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit/benefit-amount.html",
     "publisher": "Government of Canada",
     "used_for": "The optional 'realistic EI' shock, which caps EI at $729/week (about $3,159/month)."},
    {"name": "Interest rates for new and existing household lending",
     "url": "https://bankofcanada.ca/rates/banking-and-financial-statistics/interest-rates-for-new-and-existing-household-lending",
     "publisher": "Bank of Canada",
     "used_for": "The loan planner's default rate (personal loan plans, 7.92%) and the other lending rates offered."},
    {"name": "Policy interest rate (2.50%, raised 2026-10-28)",
     "url": "https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/",
     "publisher": "Bank of Canada",
     "used_for": "Context for the rate-hike shock."},
    {"name": "Prime rate in Canada",
     "url": "https://www.ratehub.ca/prime-rate",
     "publisher": "Ratehub (aggregator)",
     "used_for": "The prime rate shown alongside the lending rates."},
    {"name": "Gemini API (Google)",
     "url": "https://ai.google.dev/",
     "publisher": "Google",
     "used_for": "Turning a twist card typed in plain English into shock settings, and reading unfamiliar "
                 "statement layouts. Only card text or masked statement text is sent; no dataset rows."},
]
