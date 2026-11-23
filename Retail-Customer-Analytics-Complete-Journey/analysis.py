"""
analysis.py
Retail Customer Analytics – "GreenValley Retail"
Datensatz: 84.51° Complete Journey 2.0 (2.469 Haushalte, Kalenderjahr 2017)

1. Ausgabentrend: Steigerer, Halter, Reduzierer
2. Wirkung der Direktmarketing-Kampagnen (Type A/B/C) mit Kontrollgruppe
3. Demografie: Einkommen und Kinder im Haushalt
"""
import numpy as np
import pandas as pd
import pyreadr
import matplotlib.pyplot as plt
from scipy import stats

pd.set_option("display.width", 200)
GRUEN, GRAU, ROT = "#2e8b57", "#9aa5b1", "#d9534f"


def lade(name):
    return list(pyreadr.read_r(f"data/{name}").values())[0]


# ------------------------------------------------------------
# 0. Daten laden
# ------------------------------------------------------------
trans = lade("transactions.rds")
demo = lade("demographics.rda")
produkte = lade("products.rda")
kampagnen = lade("campaigns.rda")
kampagnen_info = lade("campaign_descriptions.rda")
einloesungen = lade("coupon_redemptions.rda")

# nur Kalenderjahr 2017 (wenige Transaktionen am 01.01.2018 entfernen)
trans = trans[trans.transaction_timestamp < "2018-01-01"].copy()
trans["datum"] = trans.transaction_timestamp.dt.normalize()
trans["monat"] = trans.transaction_timestamp.dt.month

print("Transaktionen:", len(trans))
print("Haushalte:", trans.household_id.nunique())
print("Umsatz gesamt: %.0f $" % trans.sales_value.sum())
print("Umsatz H1 vs. H2: %.0f $ / %.0f $" % (trans[trans.monat <= 6].sales_value.sum(), trans[trans.monat > 6].sales_value.sum()))


# ------------------------------------------------------------
# 1. Ausgabentrend: Steigerer / Halter / Reduzierer
# ------------------------------------------------------------
# Vergleich der Ausgaben im 1. Halbjahr (Jan-Jun) mit dem 2. Halbjahr (Jul-Dez).
# Steigerer: > +10 %, Reduzierer: < -10 %, Halter: dazwischen.
trans["halbjahr"] = np.where(trans.monat <= 6, "H1", "H2")
hj = trans.pivot_table(index="household_id", columns="halbjahr",
                       values="sales_value", aggfunc="sum", fill_value=0)
# Nur dauerhaft aktive Haushalte (Käufe in mind. 10 von 12 Monaten), damit
# Haushalte, die erst im Laufe des Jahres dazukommen oder wegfallen, das Ergebnis nicht verzerren.
aktive_monate = trans.groupby("household_id").monat.nunique()
aktiv = aktive_monate[aktive_monate >= 10].index
print("Dauerhaft aktive Haushalte (>= 10 Monate):", len(aktiv))
hj = hj[hj.index.isin(aktiv) & (hj.H1 > 0) & (hj.H2 > 0)].copy()
hj["veraenderung"] = (hj.H2 - hj.H1) / hj.H1 * 100
hj["segment"] = pd.cut(hj.veraenderung, [-np.inf, -10, 10, np.inf],
                       labels=["Reduzierer", "Halter", "Steigerer"])

seg = hj.groupby("segment", observed=True).agg(
    haushalte=("H1", "size"),
    umsatz_H1=("H1", "mean"),
    umsatz_H2=("H2", "mean"),
    median_veraenderung=("veraenderung", "median"))
seg["anteil_pct"] = seg.haushalte / seg.haushalte.sum() * 100
print("\n--- 1. Segmente (dauerhaft aktive Haushalte) ---")
print(seg.round(1))

# Umsatzwirkung der Segmente
delta = (hj.groupby("segment", observed=True).apply(lambda g: (g.H2 - g.H1).sum()))
print("\nUmsatzveränderung H2 vs. H1 je Segment ($):")
print(delta.round(0))

ax = seg.anteil_pct.reindex(["Steigerer", "Halter", "Reduzierer"]).plot(
    kind="bar", color=[GRUEN, GRAU, ROT], figsize=(7, 4.5))
ax.set_ylabel("Anteil der Haushalte (%)")
ax.set_xlabel("")
ax.set_title("Ausgabentrend: 2. vs. 1. Halbjahr 2017")
for p in ax.patches:
    ax.annotate(f"{p.get_height():.0f} %", (p.get_x() + p.get_width() / 2, p.get_height()),
                ha="center", va="bottom")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig("images/segmente.png", dpi=120)
plt.close()


# ------------------------------------------------------------
# 2. Kampagnenwirkung Type A/B/C (Difference-in-Differences)
# ------------------------------------------------------------
# Vorher: durchschnittliche Wochenausgaben in den 4 Wochen vor Kampagnenstart
# Während: durchschnittliche Wochenausgaben während der Kampagne
# Danach: Ausgaben in der Woche nach Kampagnenende
# Kontrollgruppe: alle Haushalte, die die Kampagne NICHT erhalten haben.
taeglich = trans.groupby(["household_id", "datum"]).sales_value.sum().reset_index()
alle_hh = trans.household_id.unique()
start_daten, ende_daten = trans.datum.min(), trans.datum.max()


def wochen_ausgaben(hh, von, bis):
    """Durchschnittliche Ausgaben pro Haushalt und Woche im Zeitraum [von, bis)."""
    t = taeglich[(taeglich.datum >= von) & (taeglich.datum < bis) & taeglich.household_id.isin(hh)]
    wochen = (bis - von).days / 7
    return t.sales_value.sum() / len(hh) / wochen


zeilen = []
for _, k in kampagnen_info.iterrows():
    start, ende = pd.Timestamp(k.start_date), pd.Timestamp(k.end_date)
    vor_von = start - pd.Timedelta(days=28)
    nach_bis = ende + pd.Timedelta(days=8)
    if vor_von < start_daten or nach_bis > ende_daten + pd.Timedelta(days=1):
        continue   # Zeitfenster liegt nicht vollständig in 2017
    ziel = kampagnen.loc[kampagnen.campaign_id == k.campaign_id, "household_id"].unique()
    ziel = np.intersect1d(ziel, alle_hh)
    kontrolle = np.setdiff1d(alle_hh, ziel)
    for gruppe, hh in [("Ziel", ziel), ("Kontrolle", kontrolle)]:
        zeilen.append({
            "campaign_id": k.campaign_id, "typ": k.campaign_type, "gruppe": gruppe,
            "haushalte": len(hh),
            "vorher": wochen_ausgaben(hh, vor_von, start),
            "waehrend": wochen_ausgaben(hh, start, ende + pd.Timedelta(days=1)),
            "danach": wochen_ausgaben(hh, ende + pd.Timedelta(days=1), nach_bis),
        })

kamp = pd.DataFrame(zeilen)
kamp["lift_waehrend"] = (kamp.waehrend / kamp.vorher - 1) * 100
kamp["lift_danach"] = (kamp.danach / kamp.vorher - 1) * 100

breit = kamp.pivot_table(index=["campaign_id", "typ"], columns="gruppe",
                         values=["lift_waehrend", "lift_danach", "haushalte"])
did = pd.DataFrame({
    "haushalte_ziel": breit[("haushalte", "Ziel")],
    "did_waehrend": breit[("lift_waehrend", "Ziel")] - breit[("lift_waehrend", "Kontrolle")],
    "did_danach": breit[("lift_danach", "Ziel")] - breit[("lift_danach", "Kontrolle")],
}).reset_index()

print("\n--- 2. Kampagnen (Difference-in-Differences, Prozentpunkte) ---")
print("Auswertbare Kampagnen:", len(did))
nach_typ = did.groupby("typ").agg(kampagnen=("campaign_id", "count"),
                                  haushalte_mittel=("haushalte_ziel", "mean"),
                                  did_waehrend=("did_waehrend", "mean"),
                                  did_danach=("did_danach", "mean"))
print(nach_typ.round(1))
for typ in sorted(did.typ.unique()):
    werte = did.loc[did.typ == typ, "did_waehrend"]
    if len(werte) > 2:
        t, p = stats.ttest_1samp(werte, 0)
        print(f"{typ}: t-Test DiD während > 0: p = {p:.4f}")

# Coupon-Einlösequote je Typ
eingeloest = einloesungen.groupby("campaign_id").household_id.nunique()
erhalten = kampagnen.groupby("campaign_id").household_id.nunique()
quote = (eingeloest / erhalten).rename("quote").reset_index().merge(
    kampagnen_info[["campaign_id", "campaign_type"]], on="campaign_id")
quote_typ = quote.groupby("campaign_type").quote.mean() * 100
print("\nAnteil der Zielhaushalte mit mindestens einer Coupon-Einlösung (%):")
print(quote_typ.round(1))

fig, ax = plt.subplots(figsize=(7, 4.5))
x = np.arange(len(nach_typ))
ax.bar(x - 0.2, nach_typ.did_waehrend, 0.4, label="während der Kampagne", color=GRUEN)
ax.bar(x + 0.2, nach_typ.did_danach, 0.4, label="Woche nach Kampagnenende", color=GRAU)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x, nach_typ.index)
ax.set_ylabel("Mehrumsatz ggü. Kontrollgruppe (Prozentpunkte)")
ax.set_title("Kampagnenwirkung je Typ (Difference-in-Differences)")
ax.legend()
plt.tight_layout()
plt.savefig("images/kampagnen.png", dpi=120)
plt.close()


# ------------------------------------------------------------
# 3. Demografie: Einkommen und Kinder
# ------------------------------------------------------------
jahr = trans.groupby("household_id").sales_value.sum().rename("jahresumsatz").reset_index()
d = demo.merge(jahr, on="household_id")
hoch = ["75-99K", "100-124K", "125-149K", "150-174K", "175-199K", "200-249K", "250K+"]
niedrig = ["Under 15K", "15-24K", "25-34K"]
d["einkommen"] = np.select([d.income.isin(hoch), d.income.isin(niedrig)],
                           ["hoch (>75K)", "niedrig (<35K)"], "mittel")
d["kinder"] = np.where(d.kids_count.astype(str) == "0", "ohne Kinder", "mit Kindern")

print("\n--- 3. Demografie (Haushalte mit Demografiedaten: %d) ---" % len(d))
for spalte, a, b in [("einkommen", "hoch (>75K)", "niedrig (<35K)"),
                     ("kinder", "mit Kindern", "ohne Kinder")]:
    ga, gb = d.loc[d[spalte] == a, "jahresumsatz"], d.loc[d[spalte] == b, "jahresumsatz"]
    t, p = stats.ttest_ind(ga, gb, equal_var=False)
    print(f"{a:16s}: n={len(ga):3d}  Ø {ga.mean():7.0f} $ | {b:16s}: n={len(gb):3d}  Ø {gb.mean():7.0f} $"
          f" | Diff {ga.mean() / gb.mean() * 100 - 100:+.0f} %  p = {p:.4f}")

# Kategorie-Präferenzen: Anteil am Warenkorb, hoch vs. niedrig
tp = trans.merge(produkte[["product_id", "product_category"]], on="product_id") \
          .merge(d[["household_id", "einkommen", "kinder"]], on="household_id")


def kategorie_anteile(spalte):
    k = tp[~tp.product_category.fillna("").str.contains("COUPON")].groupby([spalte, "product_category"]).sales_value.sum()
    return (k / k.groupby(level=0).transform("sum") * 100).unstack(0).fillna(0)


anteil_ek = kategorie_anteile("einkommen")
anteil_ek["diff"] = anteil_ek["hoch (>75K)"] - anteil_ek["niedrig (<35K)"]
print("\nKategorien mit dem größten Anteilsunterschied (hoch minus niedrig, Prozentpunkte):")
print(anteil_ek["diff"].sort_values().iloc[np.r_[0:5, -5:0]].round(2))

anteil_ki = kategorie_anteile("kinder")
anteil_ki["diff"] = anteil_ki["mit Kindern"] - anteil_ki["ohne Kinder"]
print("\nKategorien mit dem größten Anteilsunterschied (mit minus ohne Kinder, Prozentpunkte):")
print(anteil_ki["diff"].sort_values().iloc[np.r_[0:5, -5:0]].round(2))

reihenfolge = ["niedrig (<35K)", "mittel", "hoch (>75K)"]
mittel_ek = d.groupby("einkommen").jahresumsatz.mean().reindex(reihenfolge)
mittel_ki = d.groupby("kinder").jahresumsatz.mean().reindex(["ohne Kinder", "mit Kindern"])
fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
axes[0].bar(mittel_ek.index, mittel_ek.values, color=[GRAU, GRAU, GRUEN])
axes[0].set_title("Jahresumsatz nach Einkommen")
axes[0].set_ylabel("Ø Jahresumsatz pro Haushalt ($)")
axes[1].bar(mittel_ki.index, mittel_ki.values, color=[GRAU, GRUEN])
axes[1].set_title("Jahresumsatz nach Kindern im Haushalt")
plt.tight_layout()
plt.savefig("images/demografie.png", dpi=120)
plt.close()

print("\nFertig.")
