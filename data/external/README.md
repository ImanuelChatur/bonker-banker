# External reference data

Small public tables used alongside the datathon dataset. Committed to the repo (unlike `data/raw/`).
Every row also carries its own `source_name` and `source_url` columns.

| File | What it holds | Sources |
| :-- | :-- | :-- |
| `canadian_lending_rates_2026.csv` | Bank of Canada policy rate (2.50%, raised 2026-10-28), prime rate, and new-lending rates for personal loans, auto loans, lines of credit, credit cards and mortgages (2026-08). Used for the loan affordability check and the rate-hike shock. | [Bank of Canada: policy interest rate](https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/); [Bank of Canada: interest rates for new and existing household lending](https://bankofcanada.ca/rates/banking-and-financial-statistics/interest-rates-for-new-and-existing-household-lending) (series V122667780 to V122667812); [Ratehub: prime rate in Canada](https://www.ratehub.ca/prime-rate) (aggregator, for prime only) |
| `ei_parameters_2026.csv` | EI regular benefits: 55% benefit rate, $729/week maximum, $68,900 maximum insurable earnings, 14 to 45 benefit weeks. Used for the optional "realistic EI" shock. | [Government of Canada: EI regular benefits, how much you could receive](https://www.canada.ca/en/services/benefits/ei/ei-regular-benefit/benefit-amount.html) |
