# Publish guide — MAKD-Natality (DRAFT)

Nothing here was pushed or submitted from the build session: no GitHub or Zenodo token was supplied, and arXiv and journal submission require your personal attestation. Do these only after every box in `docs/VERIFY_CHECKLIST.md` is ticked and `python code/publish_gate.py . --allow-draft-in code/ tests/` passes (code and tests contain the stamping logic itself, so they are scanned as warnings, not blockers).

Author block for every form (from `AUTHORS.json`): **Selorm Buaka**, University of Northern Colorado, ORCID 0009-0005-3991-4859, email [VERIFY].

## 1. GitHub (target: January 2027)
1. github.com/new → name `makd-natality`, public, empty (no README).
2. In the project folder:
   ```
   git init -b main
   git add -A
   git commit -m "MAKD-Natality v0.1.0"
   git remote add origin https://github.com/<your-user>/makd-natality.git
   git push -u origin main
   ```
   `.gitignore` already excludes `data/raw`, `data/processed` parquet and models.
3. Releases → Draft a new release → tag `v0.1.0`, title "MAKD-Natality v0.1.0", notes: "Code and outputs for the methods preprint. No NCHS microdata included; see README to reproduce."

## 2. Zenodo DOI (same day)
1. Log in at zenodo.org with ORCID.
2. Account → GitHub → enable `makd-natality`, then publish the GitHub release (step 1.3). Zenodo mints a DOI in minutes.
3. Edit the Zenodo record: creators from AUTHORS.json with ORCID; license MIT (code); keywords: knowledge distillation, missing data, birth certificates, low birthweight, preterm birth, clinical prediction.
4. Put the DOI in `CITATION.cff`, the README status line, and `code/08_manuscript.py` (`code_doi`), then rebuild the manuscript.

## 3. arXiv stat.ME (target: February 2027)
1. Endorsement: a first submission in stat.ME may need an endorser (arxiv.org/auth/endorse). Ask Dr. Merchant or another stat.ME author early (January). Request note: "I am preparing a methods preprint on knowledge distillation for prediction under jurisdiction-specific missing data in U.S. birth certificates and would be grateful for an endorsement for stat.ME. My endorsement code is ____."
2. Build the PDF from the final manuscript (Word or LaTeX).
3. arxiv.org/submit: title exactly as in the manuscript; authors exactly as AUTHORS.json; abstract (≤1,920 characters); primary stat.ME, cross-list stat.AP; license CC BY 4.0; comments: "N pages, 4 figures. Code: https://doi.org/<Zenodo DOI>".
4. Moderation: 1–3 business days. Record the arXiv ID in the evidence log.

Note on journal policy: Statistics in Medicine and American Journal of Epidemiology both accept preprinted submissions [VERIFY current policy on each journal's author-guidelines page before posting].

## 4. Journal submission (target: March 2027)
Statistics in Medicine (Wiley ScholarOne) or American Journal of Epidemiology (Oxford, ScholarOne). Kit to assemble: manuscript (journal template), figures at 300 dpi (`paper/figures`, rebuilt with `--final`), supplement (tables S1–S4 from `paper/tables`), TRIPOD+AI checklist, cover letter citing the arXiv ID, AI-use statement per the journal's policy, data availability statement (public NCHS/WONDER sources, code DOI). Mention the submitted Ghana neonatal manuscript only as permitted by that journal's policy.

## 5. Evidence log (the same day as each step)
```
date,artifact_or_event,type,venue_or_host,link_or_doi,status,prong_tags,metrics_snapshot,files_saved,notes
YYYY-MM-DD,MAKD-Natality v0.1.0 code release,software,Zenodo + GitHub,10.5281/zenodo.NNNNNNN,live,,0 downloads at release,release_page.pdf; zenodo_record.pdf,
YYYY-MM-DD,MAKD-Natality methods preprint,preprint,arXiv stat.ME,arXiv:NNNN.NNNNN,announced,,,arxiv_abs.pdf,
YYYY-MM-DD,MAKD-Natality manuscript,journal submission,Statistics in Medicine,manuscript ID,submitted,,,submission_confirmation.pdf,
```
