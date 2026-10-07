# Exporting state item-missingness from CDC WONDER (manual, about 20 minutes)

The WONDER API does not serve sub-national natality queries, so these six exports are done by hand in the web interface. Labels below are the exact WONDER menu names (Natality, 2016-2024 expanded, checked 2026-10-07).

1. Open https://wonder.cdc.gov/natality-expanded-current.html and accept the data use restrictions.
2. Section 1, Group Results By: **State of Residence**, then **Year**, then the item variable (table below).
3. Location: all states. Year: select **All Years**. The form defaults to the latest year only, and a one-year export is the easiest mistake to make.
4. Leave all other sections at "All". Do not filter plurality; the parser uses WONDER's state totals as denominators.
5. Other options: check **Export Results** and set the format to **TSV**; check Show Zero Values and Show Suppressed Values. WONDER may disable totals when cells are suppressed; the parser then sums the category cells.
6. Click Send. Save the downloaded `.txt` into `data/wonder/` with the file name below.
7. Repeat for each item. Then run `python code/03_wonder.py` and `python code/04_qa.py`; section 5 of the QA report reconciles WONDER's national unknown rate against the public-use file. A gap above 0.5 points means the wrong variable was exported or the layout is off.

| Item | WONDER variable (look for) | Save as |
|---|---|---|
| Month prenatal care began | Month Prenatal Care Began | `wonder_precare.txt` |
| Pre-pregnancy BMI | Mother's Pre-pregnancy BMI | `wonder_bmi.txt` |
| WIC | WIC (Mother's WIC participation) | `wonder_wic.txt` |
| Smoking | Number of Cigarettes Before Pregnancy Recode (matches CIG_0; not "Tobacco Use", which covers the whole pregnancy) | `wonder_cig.txt` |
| Mother's education | Mother's Education | `wonder_meduc.txt` |
| Payer | Source of Payment for Delivery | `wonder_pay.txt` |

Rows labeled "Unknown or Not Stated", "Not Reported", or "Not Available" are counted as missing (`config.yaml` → `wonder.unknown_regex`). Suppressed cells (1–9 births) are set to 5 (`wonder.suppressed_value`) and counted in the QA report.

Log each export: append a line to `data/raw/PROVENANCE.txt` with `python code/provenance.py data/wonder/<file> https://wonder.cdc.gov/natality-expanded-current.html --log data/raw/PROVENANCE.txt --note "WONDER export, group by state, year, <item>"`.

## Exports used for v0.1 (2026-10-07)
All six exported 2026-10-07 from Natality, 2016-2024 expanded: grouped by State of Residence, Year, item; all years; 51 jurisdictions x 9 years each. Reconciliation against the 2024 public-use file: national unknown rates agree within 0.01 percentage points for every item (see data/processed/qa_report.txt).

WONDER terms: do not publish counts of 1-9 births. `data/processed/state_rates.csv` contains small counts and stays local; publish rates or suppressed tables only.
