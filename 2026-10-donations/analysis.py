"""Analysis for the 2026-10 donations column (script form of donations-analysis.ipynb).

Reads only data/processed/ and writes output/. No network.
"""
import itertools, json, warnings
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import igraph as ig, leidenalg as la
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
PROC = Path("data/processed"); OUT = Path("output"); OUT.mkdir(exist_ok=True)
SEED = 7
COUNCIL_YEARS = [2015, 2017, 2019, 2021, 2023, 2025, 2026]
C = {"A": "#b5651d", "B": "#2a6f97", "AB": "#6c757d", "": "#bbbbbb", "ink": "#222222", "grid": "#e6e6e6", "accent": "#c2185b"}
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": C["grid"], "figure.dpi": 130})

E = pd.read_csv(PROC / "donor-campaign-edges.csv")
D = pd.read_csv(PROC / "donors.csv", dtype={"zip": str})
CAMP = pd.read_csv(PROC / "campaigns.csv", dtype={"votes": str, "elected": str}).fillna({"slate_side": "", "slate_groups": ""})
SL = pd.read_csv(PROC / "group-slates.csv")
EE = pd.read_csv(PROC / "endorser-campaign-edges.csv")
EN = pd.read_csv(PROC / "endorser-nodes.csv")
camp_side = dict(zip(CAMP.campaign_id, CAMP.slate_side.fillna("")))
camp_kind = dict(zip(CAMP.campaign_id, CAMP.kind))
camp_name = dict(zip(CAMP.campaign_id, np.where(CAMP.kind == "candidate", CAMP.candidate_sov, CAMP.committee)))

# ----------------------------------------------------------------------------- projections
def project(edges, left="donor_id", right="campaign_id", w="dollars"):
    """One-mode projection of `left` nodes through shared `right` nodes: shared count and min-dollar weight."""
    acc = defaultdict(lambda: [0, 0.0])
    for _, g in edges.groupby(right):
        items = sorted(zip(g[left], g[w]))
        for (a, da), (b, db) in itertools.combinations(items, 2):
            x = acc[(a, b)]; x[0] += 1; x[1] += min(da, db)
    if not acc: return pd.DataFrame(columns=["u", "v", "shared", "min_dollars"])
    return pd.DataFrame([(a, b, s, m) for (a, b), (s, m) in acc.items()], columns=["u", "v", "shared", "min_dollars"])

def graph(proj, nodes=None, weight="shared"):
    G = nx.Graph()
    if nodes is not None: G.add_nodes_from(nodes)
    for r in proj.itertuples(): G.add_edge(r.u, r.v, weight=getattr(r, weight), shared=r.shared, min_dollars=r.min_dollars)
    return G

def leiden(G, weight="weight", seed=SEED):
    if G.number_of_edges() == 0: return {}, float("nan")
    nodes = list(G.nodes()); idx = {n: i for i, n in enumerate(nodes)}
    g = ig.Graph(n=len(nodes), edges=[(idx[u], idx[v]) for u, v in G.edges()]); g.es["weight"] = [G[u][v][weight] for u, v in G.edges()]
    part = la.find_partition(g, la.ModularityVertexPartition, weights="weight", seed=seed)
    return {nodes[i]: c for i, c in enumerate(part.membership)}, part.modularity

def modularity_of(G, labels, weight="weight"):
    comms = defaultdict(set)
    for n, c in labels.items():
        if n in G and c != "": comms[c].add(n)
    if len(comms) < 2: return float("nan")
    H = G.subgraph(set().union(*comms.values()))
    return nx.community.modularity(H, list(comms.values()), weight=weight)

def side_of_donor(edges_y):
    """A donor's side in a year: A if most of their candidate dollars went to slate-A candidates, B if to slate B,
    AB if split within 60/40, '' if they gave to no sided candidate (issue committees or unsided candidates only)."""
    e = edges_y[edges_y.campaign_id.map(camp_kind) == "candidate"].copy()
    e["side"] = e.campaign_id.map(camp_side)
    e = e[e.side.isin(["A", "B", "AB"])]
    tot = e.assign(a=np.where(e.side == "A", e.dollars, np.where(e.side == "AB", e.dollars / 2, 0.0)),
                   b=np.where(e.side == "B", e.dollars, np.where(e.side == "AB", e.dollars / 2, 0.0))).groupby("donor_id")[["a", "b"]].sum()
    share = tot.a / (tot.a + tot.b)
    return pd.Series(np.where(share >= 0.6, "A", np.where(share <= 0.4, "B", "AB")), index=tot.index)

def ei_index(G, labels):
    """Krackhardt E-I index on the labelled subgraph: (external - internal) / total edge weight; -1 = all ties within sides."""
    ext = intr = 0.0
    for u, v, d in G.edges(data=True):
        if u in labels and v in labels and labels[u] in ("A", "B") and labels[v] in ("A", "B"):
            if labels[u] == labels[v]: intr += d["weight"]
            else: ext += d["weight"]
    return (ext - intr) / (ext + intr) if ext + intr else float("nan")

def label_null(G, labels, n=50, seed=SEED):
    """Slate modularity when the A/B labels are shuffled among the same donors (keeps group sizes and the graph)."""
    rng = np.random.default_rng(seed); nodes = list(labels); vals = np.array([labels[k] for k in nodes]); qs = []
    for _ in range(n):
        rng.shuffle(vals); qs.append(modularity_of(G, dict(zip(nodes, vals))))
    return float(np.nanmean(qs)), float(np.nanstd(qs))

def null_modularity(edges_y, labels, n=20, seed=SEED):
    """Modularity of the slate partition on projections of degree-preserving rewirings of the bipartite graph
    (configuration model on the donor-campaign edge list, weights kept with the donor). Returns mean and sd."""
    rng = np.random.default_rng(seed); qs = []
    e = edges_y[["donor_id", "campaign_id", "dollars"]].reset_index(drop=True)
    for _ in range(n):
        camps = e.campaign_id.values.copy(); rng.shuffle(camps)
        r = e.assign(campaign_id=camps).drop_duplicates(["donor_id", "campaign_id"])
        G = graph(project(r))
        qs.append(modularity_of(G, labels))
    return float(np.nanmean(qs)), float(np.nanstd(qs))

# ----------------------------------------------------------------------------- annual donor networks
rows = []; annual = {}; donor_side = {}
for y in sorted(E.year.unique()):
    ey = E[E.year == y]
    P = project(ey); G = graph(P, nodes=ey.donor_id.unique())
    lab, q = leiden(G)
    sides = side_of_donor(ey); donor_side[y] = sides
    slab = {d: s for d, s in sides.items() if s in ("A", "B")}
    q_slate = modularity_of(G, slab)
    qn, qsd = null_modularity(ey, slab, n=10) if y in COUNCIL_YEARS else (np.nan, np.nan)
    ql, qlsd = label_null(G, slab) if y in COUNCIL_YEARS else (np.nan, np.nan)
    cross = (sides == "AB").mean() if len(sides) else np.nan
    n_c = ey.campaign_id.nunique(); n_d = ey.donor_id.nunique()
    deg = pd.Series(dict(G.degree())).reindex(ey.donor_id.unique()).fillna(0)
    multi = (ey.groupby("donor_id").campaign_id.nunique() > 1).mean()
    rows.append(dict(year=y, donors=n_d, campaigns=n_c, candidate_campaigns=int((ey.campaign_id.map(camp_kind) == "candidate").sum() and ey[ey.campaign_id.map(camp_kind) == "candidate"].campaign_id.nunique()),
                     bipartite_edges=len(ey), dollars=round(ey.dollars.sum()), projection_edges=G.number_of_edges(), density=nx.density(G), mean_degree=deg.mean(),
                     share_multi_campaign_donors=multi, leiden_Q=q, leiden_communities=len(set(lab.values())), slate_Q=q_slate, slate_Q_null_mean=qn, slate_Q_null_sd=qsd, slate_Q_label_null_mean=ql, slate_Q_label_null_sd=qlsd,
                     ei_index=ei_index(G, slab), share_sided_donors=(sides.isin(["A", "B"])).sum() / n_d, share_cross_slate=cross,
                     side_A_donors=int((sides == "A").sum()), side_B_donors=int((sides == "B").sum())))
    annual[y] = dict(G=G, lab=lab, sides=sides, P=P)
    print(y, f"donors {n_d} campaigns {n_c} edges {G.number_of_edges()} Q_leiden {q:.3f} Q_slate {q_slate:.3f} null {qn:.3f}±{qsd:.3f} cross {cross:.2f}")
A = pd.DataFrame(rows); A.to_csv(OUT / "donor-network-annual.csv", index=False)

# ----------------------------------------------------------------------------- cumulative donor networks
crow = []
for y in COUNCIL_YEARS:
    ec = E[E.year <= y]
    P = project(ec); G = graph(P, nodes=ec.donor_id.unique())
    lab, q = leiden(G)
    # cumulative side: majority of candidate dollars over all years to date
    s = side_of_donor(ec); slab = {d: v for d, v in s.items() if v in ("A", "B")}
    crow.append(dict(through_year=y, donors=ec.donor_id.nunique(), campaigns=ec.campaign_id.nunique(), projection_edges=G.number_of_edges(),
                     leiden_Q=q, leiden_communities=len(set(lab.values())), slate_Q=modularity_of(G, slab), ei_index=ei_index(G, slab),
                     share_cross_slate=(s == "AB").mean(), giant_component_share=max(len(c) for c in nx.connected_components(G)) / G.number_of_nodes()))
    print("cumulative", y, crow[-1])
CU = pd.DataFrame(crow); CU.to_csv(OUT / "donor-network-cumulative.csv", index=False)

# ----------------------------------------------------------------------------- consistency of donors across cycles
cy = E[E.year.isin(COUNCIL_YEARS)]
years_by_donor = cy.groupby("donor_id").year.apply(lambda s: sorted(set(s)))
n_cycles = years_by_donor.apply(len)
cons = dict(donors_in_council_years=int(len(n_cycles)), one_cycle=float((n_cycles == 1).mean()), two_cycles=float((n_cycles == 2).mean()),
            three_plus=float((n_cycles >= 3).mean()), five_plus=float((n_cycles >= 5).mean()), max_cycles=int(n_cycles.max()))
ret = []
for i in range(1, len(COUNCIL_YEARS)):
    y0, y1 = COUNCIL_YEARS[i - 1], COUNCIL_YEARS[i]
    d0 = set(cy[cy.year == y0].donor_id); d1 = set(cy[cy.year == y1].donor_id)
    prior = set(cy[cy.year < y1].donor_id)
    dol1 = cy[cy.year == y1].groupby("donor_id").dollars.sum()
    ret.append(dict(year=y1, donors=len(d1), returning_from_previous_cycle=len(d0 & d1) / len(d1), returning_from_any_prior_cycle=len(prior & d1) / len(d1),
                    dollars_share_from_returning=dol1[dol1.index.isin(prior)].sum() / dol1.sum(), retained_of_previous=len(d0 & d1) / len(d0)))
R = pd.DataFrame(ret); R.to_csv(OUT / "donor-retention.csv", index=False)
# side loyalty: transition matrix of sides between consecutive council elections
trans = Counter(); loyal = []
for i in range(1, len(COUNCIL_YEARS)):
    y0, y1 = COUNCIL_YEARS[i - 1], COUNCIL_YEARS[i]
    s0, s1 = donor_side.get(y0, pd.Series(dtype=object)), donor_side.get(y1, pd.Series(dtype=object))
    both = s0.index.intersection(s1.index)
    for d in both: trans[(s0[d], s1[d])] += 1
    ab = [(s0[d], s1[d]) for d in both if s0[d] in ("A", "B") and s1[d] in ("A", "B")]
    loyal.append(dict(from_year=y0, to_year=y1, repeat_sided_donors=len(ab), same_side_share=(sum(a == b for a, b in ab) / len(ab)) if ab else np.nan))
T = pd.DataFrame([(a, b, n) for (a, b), n in trans.items()], columns=["side_from", "side_to", "donors"]).pivot(index="side_from", columns="side_to", values="donors").fillna(0).astype(int)
T.to_csv(OUT / "donor-side-transitions.csv"); L = pd.DataFrame(loyal); L.to_csv(OUT / "donor-side-loyalty.csv", index=False)
json.dump(cons, open(OUT / "donor-consistency.json", "w"), indent=1)
print("consistency", cons); print(L)

# ----------------------------------------------------------------------------- other measures: concentration, candidate overlap
conc = []
for y in sorted(E.year.unique()):
    ey = E[E.year == y]; dd = ey.groupby("donor_id").dollars.sum().sort_values(ascending=False)
    x = np.sort(dd.values); n = len(x); gini = (2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum()) - (n + 1) / n) if n and x.sum() else np.nan
    conc.append(dict(year=y, donors=n, median_gift_total=float(dd.median()), top10pct_dollar_share=float(x[-max(1, n // 10):].sum() / x.sum()), gini=float(gini),
                     share_at_100_cap=float((ey.groupby("donor_id").dollars.max() >= 100).mean())))
pd.DataFrame(conc).to_csv(OUT / "donor-concentration.csv", index=False)

def candidate_overlap(edges_y, left="donor_id"):
    """Jaccard overlap of supporter sets between candidate campaigns in a year."""
    e = edges_y[edges_y.campaign_id.map(camp_kind) == "candidate"]
    sets = e.groupby("campaign_id")[left].apply(set)
    ids = list(sets.index); M = pd.DataFrame(np.eye(len(ids)), index=ids, columns=ids)
    for a, b in itertools.combinations(ids, 2):
        j = len(sets[a] & sets[b]) / len(sets[a] | sets[b]) if sets[a] | sets[b] else 0
        M.loc[a, b] = M.loc[b, a] = j
    return M

overlaps = {}
for y in COUNCIL_YEARS:
    M = candidate_overlap(E[E.year == y]); M.index = M.columns = [camp_name[c] for c in M.index]; overlaps[y] = M
    M.round(3).to_csv(OUT / f"candidate-donor-overlap-{y}.csv")

# ----------------------------------------------------------------------------- endorsement networks
EE["campaign_id"] = [f"{y}|cand|{c}" for y, c in zip(EE.year, EE.candidate_sov)]
name_to_id = {}
for r in CAMP[CAMP.kind == "candidate"].itertuples(): name_to_id[(r.year, r.candidate_sov)] = r.campaign_id
EE["campaign_id"] = [name_to_id.get((y, c), f"{y}|cand|{c}") for y, c in zip(EE.year, EE.candidate_sov)]
EE["dollars"] = 1.0
erows = []; eannual = {}
for y in sorted(EE.year.unique()):
    ey = EE[EE.year == y].drop_duplicates(["node_id", "campaign_id"])
    if ey.campaign_id.nunique() < 2: continue
    P = project(ey, left="node_id"); G = graph(P, nodes=ey.node_id.unique())
    lab, q = leiden(G)
    ey2 = ey.assign(side=ey.campaign_id.map(camp_side).fillna(""))
    sides = ey2[ey2.side.isin(["A", "B"])].groupby("node_id").side.agg(lambda s: "A" if (s == "A").mean() > 0.5 else "B" if (s == "B").mean() > 0.5 else "AB")
    slab = {n: s for n, s in sides.items() if s in ("A", "B")}
    people = ey[ey.endorser_type == "person"]
    erows.append(dict(year=y, endorsers=ey.node_id.nunique(), people=people.node_id.nunique(), organizations=ey[ey.endorser_type == "organization"].node_id.nunique(),
                      candidates_with_pages=ey.campaign_id.nunique(), edges=len(ey), projection_edges=G.number_of_edges(), density=nx.density(G),
                      leiden_Q=q, leiden_communities=len(set(lab.values())), slate_Q=modularity_of(G, slab), ei_index=ei_index(G, slab),
                      share_cross_slate=(sides == "AB").mean() if len(sides) else np.nan, share_multi_candidate=(ey.groupby("node_id").campaign_id.nunique() > 1).mean(),
                      share_people_held_elected_office=people.drop_duplicates("node_id").held_any_elected_office.mean(),
                      share_people_held_boulder_council=people.drop_duplicates("node_id").held_boulder_council.mean(),
                      share_people_board_commission=people.drop_duplicates("node_id").served_board_commission.mean()))
    eannual[y] = dict(G=G, lab=lab, sides=sides, edges=ey)
    print("endorse", y, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in erows[-1].items()})
EA = pd.DataFrame(erows); EA.to_csv(OUT / "endorsement-network-annual.csv", index=False)
# endorser consistency across years
ep = EE[EE.endorser_type == "person"].groupby("node_id").year.apply(lambda s: sorted(set(s)))
en_cycles = ep.apply(len)
econs = dict(people=int(len(en_cycles)), one_year=float((en_cycles == 1).mean()), two_plus=float((en_cycles >= 2).mean()), three_plus=float((en_cycles >= 3).mean()))
eside = {}
for y, d in eannual.items(): eside[y] = d["sides"]
eloyal = []
ys = sorted(eannual)
for y0, y1 in zip(ys, ys[1:]):
    s0, s1 = eside[y0], eside[y1]; both = s0.index.intersection(s1.index)
    ab = [(s0[d], s1[d]) for d in both if s0[d] in ("A", "B") and s1[d] in ("A", "B")]
    eloyal.append(dict(from_year=y0, to_year=y1, repeat_endorsers=len(both), repeat_sided=len(ab), same_side_share=(sum(a == b for a, b in ab) / len(ab)) if ab else np.nan))
json.dump(econs, open(OUT / "endorser-consistency.json", "w"), indent=1); pd.DataFrame(eloyal).to_csv(OUT / "endorser-side-loyalty.csv", index=False)
print("endorser consistency", econs); print(pd.DataFrame(eloyal))

# ----------------------------------------------------------------------------- donors vs endorsers: candidate-level comparison
def mantel(M1, M2, n=2000, seed=SEED):
    ids = [i for i in M1.index if i in M2.index]
    if len(ids) < 4: return np.nan, np.nan, len(ids)
    a = M1.loc[ids, ids].values; b = M2.loc[ids, ids].values; iu = np.triu_indices(len(ids), 1)
    x, yv = a[iu], b[iu]; r = np.corrcoef(x, yv)[0, 1]; rng = np.random.default_rng(seed); cnt = 0
    for _ in range(n):
        p = rng.permutation(len(ids)); bp = b[np.ix_(p, p)][iu]
        if abs(np.corrcoef(x, bp)[0, 1]) >= abs(r): cnt += 1
    return float(r), cnt / n, len(ids)

cmp_rows = []
for y in ys:
    Mo = candidate_overlap(EE[EE.year == y].drop_duplicates(["node_id", "campaign_id"]), left="node_id"); Mo.index = Mo.columns = [camp_name.get(c, c) for c in Mo.index]
    Mo.round(3).to_csv(OUT / f"candidate-endorser-overlap-{y}.csv")
    Md = overlaps.get(y)
    if Md is None: continue
    r, p, k = mantel(Md, Mo)
    # slate modularity in candidate-level projections
    def cand_graph(M):
        G = nx.Graph()
        for a, b in itertools.combinations(M.index, 2):
            if M.loc[a, b] > 0: G.add_edge(a, b, weight=M.loc[a, b])
        return G
    sd = {n: camp_side.get(name_to_id.get((y, n), ""), "") for n in Md.index}
    Gd, Ge = cand_graph(Md), cand_graph(Mo)
    cmp_rows.append(dict(year=y, candidates_compared=k, mantel_r=r, mantel_p=p, donor_overlap_slate_Q=modularity_of(Gd, {n: s for n, s in sd.items() if s in ("A", "B")}),
                         endorser_overlap_slate_Q=modularity_of(Ge, {n: s for n, s in sd.items() if s in ("A", "B")}),
                         donor_mean_within_side=float(np.mean([Md.loc[a, b] for a, b in itertools.combinations(Md.index, 2) if sd[a] == sd[b] and sd[a] in ("A", "B")] or [np.nan])),
                         donor_mean_across_side=float(np.mean([Md.loc[a, b] for a, b in itertools.combinations(Md.index, 2) if {sd[a], sd[b]} == {"A", "B"}] or [np.nan])),
                         endorser_mean_within_side=float(np.mean([Mo.loc[a, b] for a, b in itertools.combinations(Mo.index, 2) if a in sd and b in sd and sd[a] == sd[b] and sd[a] in ("A", "B")] or [np.nan])),
                         endorser_mean_across_side=float(np.mean([Mo.loc[a, b] for a, b in itertools.combinations(Mo.index, 2) if a in sd and b in sd and {sd[a], sd[b]} == {"A", "B"}] or [np.nan]))))
    print("compare", cmp_rows[-1])
CMP = pd.DataFrame(cmp_rows); CMP.to_csv(OUT / "donor-vs-endorser-comparison.csv", index=False)

# ----------------------------------------------------------------------------- figures
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
a = A[A.year.isin(COUNCIL_YEARS)]
ax[0].plot(a.year, a.leiden_Q, "o-", color=C["ink"], label="Best split (Leiden)")
ax[0].plot(a.year, a.slate_Q, "s-", color=C["accent"], label="Slate split (PLAN vs Better Boulder/Progressives)")
ax[0].fill_between(a.year, a.slate_Q_null_mean - 2 * a.slate_Q_null_sd, a.slate_Q_null_mean + 2 * a.slate_Q_null_sd, color=C[""], alpha=.5, label="Slate split, rewired null (±2 sd)")
ax[0].set_title("Modularity of the donor network, council years"); ax[0].set_ylim(bottom=min(0, a.slate_Q_null_mean.min() - 0.05)); ax[0].legend(fontsize=7, frameon=False)
ax[1].plot(a.year, a.share_cross_slate, "o-", color=C["AB"], label="Gave to both slates")
ax[1].plot(a.year, 1 - a.share_sided_donors, "s-", color=C[""], label="Gave to neither slate's candidates")
ax[1].set_title("Donors who cross or sit out the slate divide"); ax[1].set_ylim(0, 0.5); ax[1].legend(fontsize=7, frameon=False)
for x in ax: x.set_xticks(COUNCIL_YEARS)
fig.tight_layout(); fig.savefig(OUT / "fig-modularity.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 3.6))
ax.plot(R.year, R.returning_from_previous_cycle, "o-", color=C["ink"], label="Gave in the previous council election")
ax.plot(R.year, R.returning_from_any_prior_cycle, "s-", color=C["B"], label="Gave in any earlier council election (since 2015)")
ax.plot(R.year, R.dollars_share_from_returning, "^-", color=C["A"], label="Share of dollars from returning donors")
ax.set_ylim(0, 1); ax.set_xticks(R.year); ax.set_title("Returning donors, council elections"); ax.legend(fontsize=7, frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig-retention.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(4.2, 3.6))
Tn = T.reindex(index=["A", "AB", "B"], columns=["A", "AB", "B"]).fillna(0)
Tp = Tn.div(Tn.sum(axis=1), axis=0)
im = ax.imshow(Tp.values, cmap="Blues", vmin=0, vmax=1)
labels = ["PLAN side", "both", "Better Boulder/\nProgressives side"]
ax.set_xticks(range(3)); ax.set_yticks(range(3)); ax.set_xticklabels(labels, fontsize=7, rotation=30, ha="right"); ax.set_yticklabels(labels, fontsize=7)
for i in range(3):
    for j in range(3): ax.text(j, i, f"{Tp.values[i, j]:.0%}\n(n={int(Tn.values[i, j])})", ha="center", va="center", fontsize=6.5, color="white" if Tp.values[i, j] > .6 else C["ink"])
ax.set_xlabel("side in the next council election"); ax.set_ylabel("side in a council election"); ax.grid(False); ax.set_title("Repeat donors mostly keep their side", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "fig-side-transitions.png"); plt.close(fig)

for y in [2023, 2025]:
    if y not in overlaps: continue
    M = overlaps[y]; order = sorted(M.index, key=lambda n: (camp_side.get(name_to_id.get((y, n), ""), "z"), n))
    M = M.loc[order, order]
    fig, ax = plt.subplots(figsize=(5.4, 4.8)); im = ax.imshow(M.values, cmap="Purples", vmin=0, vmax=max(0.3, np.nanmax(M.values[np.triu_indices(len(M), 1)])))
    ax.set_xticks(range(len(M))); ax.set_yticks(range(len(M))); ax.set_xticklabels(M.columns, rotation=60, ha="right", fontsize=7); ax.set_yticklabels(M.index, fontsize=7)
    for t, n in zip(ax.get_yticklabels(), M.index): t.set_color(C.get(camp_side.get(name_to_id.get((y, n), ""), ""), C["ink"]))
    ax.grid(False); ax.set_title(f"Shared donors between candidates, {y} (Jaccard)", fontsize=9); fig.colorbar(im, ax=ax, shrink=.7)
    fig.tight_layout(); fig.savefig(OUT / f"fig-candidate-overlap-{y}.png"); plt.close(fig)

if len(CMP):
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(CMP.year, CMP.donor_overlap_slate_Q, "o-", color=C["ink"], label="Donor-overlap network")
    ax.plot(CMP.year, CMP.endorser_overlap_slate_Q, "s-", color=C["accent"], label="Endorser-overlap network")
    ax.set_title("How much the slate split explains candidate ties"); ax.set_ylabel("slate modularity Q"); ax.set_xticks(CMP.year); ax.legend(fontsize=7, frameon=False)
    fig.tight_layout(); fig.savefig(OUT / "fig-donor-vs-endorser.png"); plt.close(fig)

print("done")
