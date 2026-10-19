# data

[`budget-survey-public.csv`](budget-survey-public.csv) is the public, de-identified file of the 216 budgets that readers submitted to the [Balance Boulder's Budget](https://boulderreportinglab.org/2026/10/04/think-you-can-balance-boulders-budget-try-closing-the-citys-6-3-million-gap/) interactive between Oct. 4 and 11, 2026, and that the *Charting Boulder* follow-up column analyzes. It holds each reader's budget, every slider as they left it, and five of the 14 optional survey answers. The analysis notebook, [`../budget-survey-analysis.ipynb`](../budget-survey-analysis.ipynb), runs on it by default and reproduces every analysis in the column from it.

**License:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit *Charting Boulder* (Brian C. Keegan), Boulder Reporting Lab. The repository's code is MIT.

## What a row is

One row per budget: 216 rows, 35 columns. The respondents chose to take part, so the rows describe the people who balanced a budget, not Boulder. Section 6 of the notebook compares them with the 2024 American Community Survey.

| Column | Values | Meaning |
|---|---|---|
| `budget_id` | `B001`–`B216` | A pseudonym for this file only. It is not the database's id and links to nothing. |
| `gf_police`, `gf_genadmin`, `gf_fire`, `gf_hhs`, `gf_manager`, `gf_it`, `gf_facilities`, `gf_finance`, `gf_parksrec`, `gf_attorney`, `gf_other` | −25 to 25 | The General Fund department sliders: the percent change from the department's estimated 2027 status quo. 0 means the reader left it alone. |
| `fund_utilities` … `fund_other` (11 columns) | −25 to 25 | The locked sliders: each department's spending outside the General Fund. Moving one cannot close the gap, and no reader moved one, so every value is 0. |
| `rev_fees`, `rev_property`, `rev_sales` | −25 to 25 | Percent change in fees and charges, the property tax and the sales and use tax. |
| `rev_marijuana` | 0 to 10 | The recreational marijuana tax rate the reader chose, in percent (3.5 today). |
| `rev_shift` | 0 to 5 | \$M of General Fund costs the reader moved onto voter-dedicated funds. |
| `spend_change` | \$M | The widget's own total: the signed change in General Fund spending (negative is a net cut). |
| `revenue_only` | \$M | The widget's own total: the signed change in recurring revenue (negative is a net tax or fee cut). |
| `demo_tenure` | Own · Rent · Other · Prefer not to say | Whether the reader owns or rents their home. |
| `demo_age` | 18-24 · 25-34 · 35-44 · 45-54 · 55-64 · 65 and over · Prefer not to say | Age. |
| `demo_education` | No high school diploma · High school diploma · GED · Some college, no degree · Associate degree · Bachelor's degree · Master's degree · Professional degree (MD, JD, DDS) · Doctoral degree (PhD, EdD) · Prefer not to say | Highest degree. |
| `demo_income` | Less than \$25,000 per year · \$25,000 to \$49,999 per year · \$50,000 to \$99,999 per year · \$100,000 to \$149,999 per year · \$150,000 to \$299,999 per year · \$300,000 per year or more · Prefer not to say | Household income. |
| `demo_building` | Single-unit house detached from any other houses · Building with two or more homes (duplex, townhome, apartment or condominium) · Manufactured home · Other · Prefer not to say | Housing type. |

A blank survey cell means the reader skipped that question. Readers had to answer at least one of the 14 survey questions to submit; two answered none of these five. The answers are exactly as readers gave them, in the widget's wording. The notebook's "The widget's numbers" section turns slider positions into dollars, and [`../embed/PROVENANCE.md`](../embed/PROVENANCE.md) traces each slider's starting point to the city's budget documents.

## How it was made, and what it leaves out

[`../pipeline/make-public-data.py`](../pipeline/make-public-data.py) builds this file from the private export of the project's Supabase database. It keeps the 216 budgets the notebook analyzes and drops:

- **test submissions** and **second budgets from the same browser**, which the column promised to set aside;
- **every time**: when the database received each budget and the reader's own clock;
- **the database's row id**, the widget version and the full submitted payload;
- **nine of the 14 survey items**, the ones the column did not analyze: years in the Boulder Valley, area of town, employment, commute, student status, race and ethnicity, gender, LGBTQ+ identity and disability.

Rows keep the database's order by row id, a random UUID that says nothing about when a budget arrived, and `budget_id` numbers them in that order. The notebook reads every file in the same order, so it gets the same results from this file as from the private export.

The database never held a name, email address, IP address, cookie or browser fingerprint with a response. The interactive told readers their submissions were anonymous. ([`../ARCHITECTURE.md`](../ARCHITECTURE.md) documents the privacy model.)

## Re-identification

Removing names is not the same as making a row impossible to trace. The five survey answers are published as readers gave them, and on those five alone, 79 of the 216 rows have a combination that no other row shares. Someone who already knew a respondent's tenure, age, education, income and housing type, and that they took part, could find that respondent's budget. Please don't try. If you believe a row identifies someone, contact Boulder Reporting Lab and it will be removed.

## What it cannot reproduce

The notebook runs from this file with these exceptions, each marked where it occurs:

- the count of budgets by day and the date range, which need submission times;
- the screen of the two exploratory survey items the notebook also checks (years in the Boulder Valley, gender);
- survey-completion figures across all 14 items, which become figures across these five.

Every figure the column reports reproduces.
