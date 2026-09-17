# Proof-run findings

What `proof-run.py` established by fetching and parsing real files on 2026-09-17. Machine-readable results are in `proof-run.json`; every file it downloaded is listed with its URL, byte count and SHA-256 in `../data/raw/manifest.json`.

The run covers three years, each chosen to break a different assumption: **2001** (CDE publishes school-by-grade as PDF only), **2013** (CDE publishes both PDF and XLS, and the staff report is school grain), and **2024** (the current XLSX era). NCES CCD was pulled for the same years through the Urban Institute API.

## Coverage, as measured rather than assumed

| Measure | Grain | Years available | Format |
|---|---|---|---|
| Enrollment by grade | School | 2000–2025 | PDF only in 2000–2002; PDF + XLS 2003–2018; XLSX 2019–2025 |
| Enrollment by grade | District | 1977–2025 | Scanned PDF to 1999; XLS/XLSX after |
| Teacher FTE | School | ~2013–2025, not every year | PDF to 2019; XLSX after |
| Teacher FTE | District | 1986–2025 | Yearbook Table 1; the annual ratio reports |
| Enrollment by grade + teacher FTE | School | 1986–2023 | NCES CCD, JSON over an API |

## A1 — The 1986–1999 yearbooks hold no school-level table

Every table in the ED2/79.19 yearbooks is by school **district**. The 1995 contents list runs: state trends by district, selected district data, membership by district and grade, membership by district and ethnic group, district rankings, graduates by district. There is no school-by-school table in the series. Those fourteen volumes therefore cannot feed a school-level archive, whatever is done about the OCR.

## A2 — The yearbooks do hold district history back to 1977

The 1986 volume carries **Table 4: Trends in Enrollment 1977-78 – 1986-87 by School District** across pages 44–61 — ten years for every district, on four measures each (fall membership, closing-day membership, average daily membership, ADAE). Illustration 1 adds state membership by grade band from 1976, and Illustration 2 adds state totals and projections 1977–91. This extends the district panel nine years earlier than the 1986 volume's own count year.

## A3 — The scans' embedded OCR keeps words and loses numbers

The volumes are page images with an invisible OCR text layer (115 pages, one JPEG each, about 108 MB per volume). The layer decodes, but it preserves headings and names far better than numeric columns:

| Table in the 1986 volume | What it holds | Numbers recovered |
|---|---|---|
| Table 4 — district trends 1977–1986 | 110 district blocks × 40 cells | **58.2%** |
| Table 2 — district × grade | 176 districts × 16 grade columns | **3.9%** |
| Table 1 — schools, staff, pupil/teacher ratio | headers decode; body does not | **~0%** |

Recovered figures are also corrupted in ways a checksum will catch but a parser will not: "1,027" reads as "027", "1,019.9" as "019.9", the column header "1981-82" as "1961-682", and "MEMBERSHIP" variously as "NEMBERSHIP" and "MEMEERSHIP". **The embedded text layer is not usable for the numeric grid.** These volumes need a fresh OCR pass over the page images. `datalab-ocr.py` does that; findings A13 to A16 record the result.

## A4 — The Artemis indexes put each link before its label

On the Artemis year pages the `<a>` element comes **before** the text naming the report. A scraper that takes the nearest preceding text silently fetches the wrong file. This run hit the bug: it first downloaded `ed288201307internet.pdf` as the 2013 pupil–teacher ratio, and that file is actually "Count of teachers by district, ethnicity and gender". The correct file is `ed288201308internet.pdf`. Any retrieval step must read the label that *follows* the link, and must then verify the file's own title page against the label before trusting it.

Two related label defects, both to be recorded rather than corrected in place: the ED2/79.19 index lists the 1998 volume as "1988" while the filename is `ed279191998internet.pdf`; and the 2013 membership index lists a "Fall 2012" school-by-ethnicity file inside the 2013 year.

## A5 — Kindergarten arrives in two columns

CDE splits kindergarten into **Half-Day K** and **Full-Day K**. CCD and the pre-2000 district tables carry one undivided K. Summing the two is the archive's first cleaning rule. Grades are also written as ordinals (`1st` … `12th`), not bare numbers, which defeats a naive header match.

## A6 — The identifier columns drift between eras

2013 heads its columns `COUNTY CODE, COUNTY NAME, DISTRICT CODE, DISTRICT NAME, SCHOOL CODE, SCHOOL NAME`. 2024 drops county entirely and renames the district pair to `Organization Code, Organization Name`. Both must map onto one schema. Codes are zero-padded four-digit strings and must not be read as numbers — a spreadsheet reader turns `0010` into `10.0`.

## A7 — CCD changed its state-school-id format in 2016

Through 2015 the CCD `seasch` field is a bare four-digit CDE school code (`1608`). From 2016 it is `<district>-<school>` (`0520-1608`). The change is exactly at the 2015/2016 boundary. A crosswalk that assumes one shape matches nothing on the other side of it — this run's first attempt matched 0 of 1,904 schools in 2024 for precisely that reason. Taking the part after the hyphen spans both eras and lifted the match to 1,823.

## A8 — CCD publishes no pre-kindergarten for Colorado

The CCD grade file carries grade codes 0 (kindergarten) through 12, plus 99 (school total). There are **no pre-K rows at all**, in any year checked. CDE's PK is roughly 31,800 pupils a year. PK is therefore a CDE-only measure, and must be recorded as *missing* on the CCD side rather than as zero. CCD also uses **negative values as missing-data sentinels** (13 such rows in 2013); they must be dropped, not summed.

## A9 — The two sources agree, once PK is set aside

Comparing the same year, 2013, school by school on the state code:

| | |
|---|---|
| Schools in CDE / in CCD / matched | 1,826 / 1,790 / **1,781** |
| CDE total, all grades | 876,999 |
| CCD total, all grades | 845,032 |
| Gap, all grades | 31,967 |
| CDE pre-K | 31,741 |
| **Gap once pre-K is excluded** | **226** — 0.03% of the state |
| Schools agreeing exactly | 1,257 of 1,781 (70.6%) |
| Median absolute difference per school | **0** |
| Largest difference at any one school | 268 |

Two independently collected sources landing within 0.03% statewide is strong evidence that both parsers are reading the tables correctly. The residual 226 and the 524 schools that differ are the reconciliation report's job, not a reason to prefer one source.

The 2024 row of `proof-run.json` shows a much wider gap (15,631 excluding PK, only 36 schools agreeing exactly). That is expected and is the point of printing it: CCD ends at 2023, so the comparison is 2024 against 2023 — a real year of change, not a parsing error. The archive must never align those two silently.

## A10 — The 2000s Artemis PDFs are born-digital, not scans

`membership-2001.pdf` has 57 pages, zero images and a full text layer. It is a generated PDF, not a scan, so the 2000–2002 school-by-grade tables are extractable without OCR. One caveat: the text layer is kerning-split, so `604` arrives as `6 0 4` and `516` as `5 1 6`. Extraction must use character positions and column boundaries, not string splitting. The row totals give a per-row checksum — for `BERTHA HEID ELEMENTARY SCHOOL` the grade cells 140 + 154 + 157 + 153 sum to the printed total of 604, which confirms both the column boundaries and the digit reassembly.

## A11 — The current FTE file carries its own enrollment count

`2024-2025PupilTeacherRatiobySchool.xlsx` has columns `School Year, LEA Code, School Code, School Name, Enrollment Count, Teacher FTE, Pupil/Teacher FTE Ratio` — 1,882 schools and 52,709.5 teacher FTE statewide. Because it carries its own enrollment count, it validates the join against the membership file rather than merely joining to it. Any school where the two enrollment figures disagree is a crosswalk fault to investigate.

## A12 — CCD coordinates are usable from 2013, thin before

Schools with a usable latitude: 1,179 of 1,680 in 2001, but **1,860 of 1,860 in 2013 and 1,950 of 1,950 in 2023**. Earlier years also carry sentinel values such as `-2.0` that must not be read as a real coordinate. Buildings should therefore be located from a recent CCD directory and carried backward by school identifier, not read from each year's own directory.

## A13 — Re-OCR through Datalab recovers the scanned tables in full

`datalab-ocr.py` sends the page images of the wanted tables to the Datalab convert API in accurate mode. On the same 1986 pages that the embedded layer could not read, it returns the complete grid. Table 2 comes back with all fourteen grade columns plus special education, ungraded and total; Table 4 comes back with all ten year columns on all four measures, with thousands separators and decimals intact, and with the column header correctly read as "1981-82".

## A14 — The row totals confirm the re-OCR, they do not merely look right

Every row in these tables carries its own printed total, which gives a checksum the OCR cannot fake. In the re-OCR of the 1986 Table 2, `CALHAN RJ-1` sums across its sixteen cells to exactly the printed 370, and `HARRISON 2` to exactly the printed 9,463. In Table 4 the four measures for `MAPLETON 1` land on a 1986-87 fall membership of 4,997, which is what Table 2 independently reports for the same district in the same volume. **The cleaning step must run this checksum on every row and record the failures**, because it is the only mechanical proof that a scanned row was read correctly.

## A15 — The default Python user agent is blocked

Datalab sits behind Cloudflare, which rejects `Python-urllib/3.x` with error 1010 before the request reaches the API. Every call returns 403 and the API key looks broken when it is not. Any ordinary user-agent string passes. This cost one confused debugging round and is recorded so the next person does not repeat it.

## A16 — The whole scanned tier costs about five dollars

Accurate mode bills **0.75 cents a page**. The 1986 volume needed 48 pages — only the three wanted tables, located from the cheap embedded text layer rather than by sending the whole book — and cost 35.25 cents. Fourteen volumes at that rate is roughly **$5.00** and a few hours of wall-clock time against the free tier's 10 requests a minute. Sending every page of every volume instead would be about 1,680 pages and $12.60, so the page-selection step saves real money but is not the difference between possible and impossible.

## What is still unknown

- Whether every year from 2003 to 2018 publishes the school-by-grade XLS, or only some. The audit step must check all 26, not three.
- Which years' staff reports are school grain. 2013 and 2016–2019 are; 2014 and 2015 are district grain by their titles. This has to be resolved file by file, by opening each one, because the titles are not reliable.
- Whether CCD 2024 has been released since this run.
