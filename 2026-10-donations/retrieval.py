"""Retrieval for the 2026-10 donations column (script form of donations-retrieval.ipynb).

Reads a local clone of the private boulder-voter-data archive (path in the BOULDER_VOTER_DATA
environment variable, default ../../boulder-voter-data) and writes anonymized, derived tables to
data/processed/. Nothing under data/processed names a donor or an individual endorser: people are
pseudonymous ids assigned by a seeded shuffle, and the mapping is not written anywhere.
Campaigns, committees, candidates and organizations keep their names: they are public actors.
"""
import gzip, csv, re, unicodedata, os, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ARCH = Path(os.environ.get("BOULDER_VOTER_DATA", "../../boulder-voter-data")).resolve()
PROC = Path("data/processed"); PROC.mkdir(parents=True, exist_ok=True)
YEARS = list(range(2015, 2027))
SEED = 20261003

# ----------------------------------------------------------------------------- contributions
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "md", "phd", "esq", "dds", "cpa"}
ORG_WORDS = re.compile(r"\b(llc|inc|corp|co|company|ltd|lp|llp|pc|p\.c|group|associates|partners|properties|holdings|trust|foundation|fund|committee|pac|union|local \d+|realty|homes|development|enterprises|ventures|investments|management|design|construction|architects|consulting|services|bank|church|club|council|association|assn|society|alliance|coalition|action|dsa|afl|cio|ucc|neighbors|citizens|friends of|boulder county|city of)\b", re.I)

def norm_text(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()

def clean_name(first, last):
    raw = f"{first} {last}"
    is_org = bool(ORG_WORDS.search(raw)) and not re.search(r"\b(jr|sr|iii)\b", raw, re.I)
    if is_org or not first.strip():
        return "", norm_text(last if norm_text(first) == norm_text(last) else raw), True
    f = norm_text(re.sub(r"[;,].*$", "", first)); l = norm_text(re.sub(r"[;,].*$", "", last))
    l = " ".join(w for w in l.split() if w not in SUFFIXES); f = " ".join(w for w in f.split() if w not in SUFFIXES)
    return (f.split()[0] if f else ""), l, False

def money(s):
    s = (s or "").replace("$", "").replace(",", "").strip()
    return float(s) if s not in ("", "-") else 0.0

rows = []
for y in YEARS:
    p = ARCH / "contributions" / "city" / f"{y}.csv.gz"
    if not p.exists(): continue
    with gzip.open(p, "rt", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip(): (v or "").strip() for k, v in r.items()}
            f, l, is_org = clean_name(r["FirstName"], r["LastName"])
            z = re.match(r"^(\d{5})", r.get("Zip", "") or "")
            rows.append(dict(year=y, committee=r["Committee"], committee_number=r["CommitteeNumber"], committee_type=r["Type"],
                             candidate=r.get("Candidate", ""), first_clean=f, last_clean=l, is_org=is_org, zip=z.group(1) if z else "",
                             has_address="Zip" in r, amount=money(r["Contribution"]), contribution_type=r["ContributionType"],
                             anonymous=r["Anonymous"].lower() == "true", from_candidate=r["FromCandidate"].lower() == "true",
                             transaction_date=r["TransactionDate"]))
df = pd.DataFrame(rows)
df["name_clean"] = (df.first_clean + " " + df.last_clean).str.strip()
keyed = df[df.has_address]
zips_by_name = keyed.groupby("name_clean")["zip"].agg(lambda s: sorted(set(z for z in s if z)))
def donor_key(r):
    if r.has_address: return f"{r.name_clean}|{r.zip}", "name+zip"
    zs = zips_by_name.get(r.name_clean, [])
    return (f"{r.name_clean}|{zs[0]}", "name->unique prior zip") if len(zs) == 1 else (f"{r.name_clean}|", "name only")
kk = [donor_key(r) for r in df.itertuples()]
df["donor_key"] = [k for k, _ in kk]; df["link_method"] = [m for _, m in kk]

# campaign nodes: candidate committees by candidate (as the finance app spells them), issue committees by name
CAMPAIGN_TYPES = {"Official Candidate Committee", "Issue Committee", "Ballot Measure Committee"}
def campaign_id(r):
    if r.committee_type == "Official Candidate Committee" and r.candidate:
        return f"{r.year}|cand|{r.candidate}"
    return f"{r.year}|issue|{r.committee}"
df["campaign_id"] = [campaign_id(r) for r in df.itertuples()]
edge_mask = df.committee_type.isin(CAMPAIGN_TYPES) & ~df.anonymous & ~df.from_candidate & ~df.is_org & df.contribution_type.isin(["Monetary", "In-Kind"]) & (df.amount > 0)
E = df[edge_mask].groupby(["year", "donor_key", "campaign_id"], as_index=False).agg(dollars=("amount", "sum"), n_gifts=("amount", "size"), link_method=("link_method", "first"))

# pseudonymous donor ids: shuffle the sorted keys with a fixed seed; the mapping is not saved
keys = sorted(E.donor_key.unique())
rng = np.random.default_rng(SEED); perm = rng.permutation(len(keys))
donor_id = {k: f"d{perm[i]+1:05d}" for i, k in enumerate(keys)}
E["donor_id"] = E.donor_key.map(donor_id)
E["key_has_zip"] = ~E.donor_key.str.endswith("|")
E["zip"] = E.donor_key.str.split("|").str[1]
E[["year", "donor_id", "campaign_id", "dollars", "n_gifts", "link_method", "key_has_zip"]].sort_values(["year", "campaign_id", "donor_id"]).to_csv(PROC / "donor-campaign-edges.csv", index=False)

# donors table: no names
D = E.groupby("donor_id").agg(first_year=("year", "min"), last_year=("year", "max"), n_years=("year", "nunique"), n_campaigns=("campaign_id", "nunique"),
                              total_dollars=("dollars", "sum"), key_has_zip=("key_has_zip", "first"), zip=("zip", "first")).reset_index()
D.to_csv(PROC / "donors.csv", index=False)

# campaigns table
camp = df[df.committee_type.isin(CAMPAIGN_TYPES)].groupby("campaign_id").agg(year=("year", "first"), committee_type=("committee_type", "first"),
        committee=("committee", "first"), committee_number=("committee_number", "first"), candidate=("candidate", "first")).reset_index()
camp["kind"] = np.where(camp.committee_type == "Official Candidate Committee", "candidate", "issue")
totals = df[edge_mask].groupby("campaign_id").agg(n_donors=("donor_key", "nunique"), dollars_itemized=("amount", "sum")).reset_index()
camp = camp.merge(totals, on="campaign_id", how="left").fillna({"n_donors": 0, "dollars_itemized": 0})

# candidate names as the Statement of Votes spells them, from campaigns/<year>/candidates.csv, and outcomes
cand_rows = []
for y in YEARS:
    p = ARCH / "campaigns" / str(y) / "candidates.csv"
    if p.exists():
        c = pd.read_csv(p, dtype=str).fillna("")
        cand_rows.append(c)
cands = pd.concat(cand_rows, ignore_index=True) if cand_rows else pd.DataFrame(columns=["year", "candidate", "committee_candidate", "contest", "votes", "elected"])
cands["year"] = cands.year.astype(int)
cmap = {(r.year, r.committee_candidate): r for r in cands.itertuples() if r.committee_candidate}
camp["candidate_sov"] = [cmap[(r.year, r.candidate)].candidate if (r.year, r.candidate) in cmap else r.candidate for r in camp.itertuples()]
camp["contest"] = [cmap[(r.year, r.candidate)].contest if (r.year, r.candidate) in cmap else ("" if r.kind == "issue" else "council") for r in camp.itertuples()]
camp["votes"] = [cmap[(r.year, r.candidate)].votes if (r.year, r.candidate) in cmap else "" for r in camp.itertuples()]
camp["elected"] = [cmap[(r.year, r.candidate)].elected if (r.year, r.candidate) in cmap else "" for r in camp.itertuples()]

# ----------------------------------------------------------------------------- group slates (parsed.csv) -> slate labels
parsed = pd.read_csv(ARCH / "endorsements" / "guides" / "parsed.csv", dtype=str).fillna("")
parsed["year"] = parsed.year.astype(int)
slates = parsed[(parsed.level == "city") & parsed.contest.isin(["council", "mayor"]) & parsed.position.isin(["endorse", "rank-1", "rank-2"])]
slates = slates[["year", "group", "contest", "choice", "position", "reported_by"]].drop_duplicates()
slates.to_csv(PROC / "group-slates.csv", index=False)
# side labels: A = the PLAN-Boulder County slate (growth-skeptic), B = the Better Boulder / Boulder Progressives slate
# (pro-housing, progressive); AB = endorsed by both poles; blank = endorsed by neither. Other groups are not used for
# the label, because their alignment moved over the decade (Sierra Club endorsed PLAN's slate in 2015 and 2017 and
# Better Boulder's from 2019; Open Boulder sided with PLAN on three of four picks in 2025).
POLE_A = {"plan_boulder_county"}; POLE_B = {"better_boulder", "boulder_progressives"}
def side_of(year, cand):
    g = set(slates[(slates.year == year) & (slates.choice == cand)].group)
    a, b = bool(g & POLE_A), bool(g & POLE_B)
    return "AB" if a and b else "A" if a else "B" if b else ""
camp["slate_side"] = [side_of(r.year, r.candidate_sov) if r.kind == "candidate" else "" for r in camp.itertuples()]
camp["slate_groups"] = [";".join(sorted(slates[(slates.year == r.year) & (slates.choice == r.candidate_sov)].group.unique())) if r.kind == "candidate" else "" for r in camp.itertuples()]
camp.sort_values(["year", "kind", "campaign_id"]).to_csv(PROC / "campaigns.csv", index=False)

# ----------------------------------------------------------------------------- endorsers (candidate pages) -> anonymized edges
en = pd.read_csv(ARCH / "endorsements" / "endorsers.csv", dtype=str).fillna("")
en["year"] = en.year.astype(int)
feat = pd.read_csv(ARCH / "endorsements" / "endorser-features.csv", dtype=str).fillna("")
en = en[en.endorser_id != ""]
pids = sorted(en[en.endorser_type == "person"].endorser_id.unique())
perm = np.random.default_rng(SEED + 1).permutation(len(pids))
pmap = {p: f"e{perm[i]+1:05d}" for i, p in enumerate(pids)}
fe = feat.set_index("endorser_id")
def pub_id(r):
    return pmap[r.endorser_id] if r.endorser_type == "person" else "org:" + re.sub(r"[^a-z0-9]+", "-", r.endorser.lower()).strip("-")
en["node_id"] = [pub_id(r) for r in en.itertuples()]
en["held_boulder_council"] = [("Boulder City Council" in fe.loc[r.endorser_id, "elected_offices"] or "Boulder Mayor" in fe.loc[r.endorser_id, "elected_offices"]) if r.endorser_id in fe.index else False for r in en.itertuples()]
en["held_any_elected_office"] = [fe.loc[r.endorser_id, "elected_offices"] != "" if r.endorser_id in fe.index else False for r in en.itertuples()]
en["served_board_commission"] = [fe.loc[r.endorser_id, "boards_commissions"] != "" if r.endorser_id in fe.index else False for r in en.itertuples()]
en["org_type"] = [fe.loc[r.endorser_id, "org_type"] if r.endorser_id in fe.index else "" for r in en.itertuples()]
en["candidate_sov"] = en.candidate
en[["year", "candidate_sov", "node_id", "endorser_type", "org_type", "office_status_at_endorsement", "held_boulder_council", "held_any_elected_office", "served_board_commission", "section"]] \
    .rename(columns={"section": "page_section"}).sort_values(["year", "candidate_sov", "node_id"]).to_csv(PROC / "endorser-campaign-edges.csv", index=False)
nodes = en.groupby("node_id").agg(endorser_type=("endorser_type", "first"), org_type=("org_type", "first"), held_boulder_council=("held_boulder_council", "max"),
                                  held_any_elected_office=("held_any_elected_office", "max"), served_board_commission=("served_board_commission", "max"),
                                  first_year=("year", "min"), n_years=("year", "nunique"), n_candidates=("candidate", "nunique")).reset_index()
nodes.to_csv(PROC / "endorser-nodes.csv", index=False)

print("edges", len(E), "donors", len(D), "campaigns", len(camp), "slate rows", len(slates), "endorser edges", len(en), "endorser nodes", len(nodes))
