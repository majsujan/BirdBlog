#!/usr/bin/env python3
"""
make_regions.py: builds regions.json for the BirdBlog map from your eBird export.

Usage (in the repo folder, with both CSVs next to this script):
    python3 make_regions.py MyEBirdData.csv ebird_world_life_list.csv

Re-run it whenever you download a fresh eBird export, then commit regions.json.

What it makes
  regions : one bubble per eBird state/province code (e.g. NO-16), with its species list
  spots   : one dot per named location, with its species list

Privacy: locations whose name looks like a street address or an auto-named personal
spot ("21A Møllebakken, ...", "Sandan, Trøndelag, NO (63.648, 11.079)") are NOT written
as spots. Their birds still count toward the region totals.
"""
import json, re, sys
import pandas as pd

CSV = sys.argv[1] if len(sys.argv) > 1 else "MyEBirdData.csv"
LIFE = sys.argv[2] if len(sys.argv) > 2 else "ebird_world_life_list.csv"
OUT = "regions.json"

# Country names exactly as used in birdData in index.html
COUNTRY = {
    "NO": "Norway", "SE": "Sweden", "FI": "Finland", "DK": "Denmark", "IT": "Italy",
    "GB": "United Kingdom", "NL": "Netherlands", "DE": "Germany", "PL": "Poland",
    "CZ": "Czech Republic", "LV": "Latvia", "GR": "Greece", "EE": "Estonia",
    "BD": "Bangladesh", "TH": "Thailand", "AW": "Aruba", "CW": "Curaçao", "BE": "Belgium",
}

# eBird code -> display name. Edit freely. A code missing here shows as the raw code.
# NOTE: the Danish names were inferred from where the checklists are, not from eBird's list. Please check them.
REGION_NAMES = {
    "BD-2": "Chittagong", "BD-3": "Dhaka", "BD-6": "Sylhet",
    "BE-VLG": "Flanders", "BE-WAL": "Wallonia",
    "CZ-PR": "Prague", "DE-NW": "North Rhine-Westphalia",
    "DK-01": "Copenhagen", "DK-03": "West Zealand", "DK-08": "Ribe",
    "DK-10": "Ringkøbing", "DK-11": "Aarhus", "DK-13": "North Jutland",
    "EE-37": "Harju", "EE-67": "Pärnu", "FI-18": "Uusimaa", "GB-ENG": "England",
    "GR-I": "Attica", "IT-25": "Lombardy", "LV-RIX": "Riga", "PL-PM": "Pomeranian",
    "NL-DR": "Drenthe", "NL-FL": "Flevoland", "NL-GE": "Gelderland", "NL-GR": "Groningen",
    "NL-LI": "Limburg", "NL-NB": "Noord-Brabant", "NL-NH": "Noord-Holland",
    "NL-UT": "Utrecht", "NL-ZE": "Zeeland",
    "NO-02": "Akershus", "NO-03": "Oslo", "NO-04": "Hedmark", "NO-05": "Oppland",
    "NO-11": "Rogaland", "NO-15": "Møre og Romsdal", "NO-16": "Sør-Trøndelag", "NO-17": "Nord-Trøndelag",
    "SE-AB": "Stockholm", "SE-M": "Skåne", "SE-Z": "Jämtland",
    "TH-10": "Bangkok", "TH-11": "Samut Prakan", "TH-14": "Ayutthaya", "TH-20": "Chon Buri",
    "TH-23": "Trat", "TH-26": "Nakhon Nayok", "TH-30": "Nakhon Ratchasima",
}

# Location names that look private (street addresses, auto-named personal spots)
PRIVATE = re.compile(r"(\(-?\d+[.,]\d+, ?-?\d+[.,]\d+\)\s*$)|(^\d)")

d = pd.read_csv(CSV)
life = pd.read_csv(LIFE, sep=";")
species = set(life.loc[life["Category"] == "species", "Common Name"])
d = d[d["Common Name"].isin(species)].copy()          # drop slashes, spuhs, hybrids, domestics
d["cc"] = d["State/Province"].str.split("-").str[0]

names = sorted(d["Common Name"].unique())
idx = {n: i for i, n in enumerate(names)}

def sp_list(frame):
    return sorted(idx[n] for n in frame["Common Name"].unique())

# ---- spots (one per location) ----
loc = d.groupby("Location ID")
spots, spot_seen = [], {}
for lid, g in loc:
    row = g.iloc[0]
    spot_seen[lid] = dict(lat=float(row["Latitude"]), lng=float(row["Longitude"]),
                          region=row["State/Province"], cc=row["cc"])
    name = str(row["Location"])
    if PRIVATE.search(name):
        continue
    spots.append({
        "n": name,
        "lat": round(float(row["Latitude"]), 3), "lng": round(float(row["Longitude"]), 3),
        "r": row["State/Province"] if "-" in str(row["State/Province"]) and not str(row["State/Province"]).endswith("-") else row["cc"],
        "k": int(g["Submission ID"].nunique()),
        "s": sp_list(g),
    })
spots.sort(key=lambda s: -len(s["s"]))

# ---- regions (one per eBird state/province code that has a suffix) ----
regions = []
for code, g in d.groupby("State/Province"):
    if code.endswith("-") or "-" not in code:
        continue                                        # country-only places (Aruba, Curaçao)
    cc = code.split("-")[0]
    pts = [spot_seen[l] for l in g["Location ID"].unique()]
    regions.append({
        "id": code, "c": COUNTRY.get(cc, cc), "n": REGION_NAMES.get(code, code),
        "lat": round(sum(p["lat"] for p in pts) / len(pts), 3),
        "lng": round(sum(p["lng"] for p in pts) / len(pts), 3),
        "k": int(g["Submission ID"].nunique()),
        "s": sp_list(g),
    })
regions.sort(key=lambda r: (r["c"], -len(r["s"])))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"names": names, "regions": regions, "spots": spots}, f, ensure_ascii=False, separators=(",", ":"))

missing = [r["id"] for r in regions if r["n"] == r["id"]]
print(f"{OUT}: {len(regions)} regions, {len(spots)} spots, {len(names)} species")
print(f"hidden as private-looking: {len(spot_seen) - len(spots)} locations")
if missing:
    print("No display name for:", ", ".join(missing), "(add them to REGION_NAMES)")
