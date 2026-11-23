"""
generate_dataset.py
Customer Churn Prediction - WM-Sportartikel-Shop
Churn = 1: Kunde wandert nach der WM ab (Hype-Käufer)
Churn = 0: Kunde bleibt aktiv (Stammkunde)

Logik: Churn-Wahrscheinlichkeit haengt plausibel von mehreren Merkmalen ab
(Stammkunde-Status, Kaufzeitpunkt, Kaufhaeufigkeit, Recency, WM-Anteil),
kombiniert mit einem Zufallsanteil, sodass die Klassen NICHT perfekt
trennbar sind (kein Merkmal weist direkt auf die Klasse hin -> Folie 5).
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N = 800

# --- 1. Basis-Merkmale (realistische Verteilungen) ---
alter = np.clip(rng.normal(34, 10, N), 16, 75).round().astype(int)

# Kaufhaeufigkeit: rechtsschief (viele Gelegenheitskaeufer, wenige Vielkaeufer)
kaufhaeufigkeit = np.clip(rng.exponential(2.0, N), 0.2, 15).round(1)

# Gesamtausgaben: lognormal (rechtsschief)
gesamtausgaben = np.clip(rng.lognormal(5.0, 0.6, N), 20, 2000).round(2)

# Tage seit letztem Kauf: exponential (Recency)
tage_letzter_kauf = np.clip(rng.exponential(30, N), 0, 365).round().astype(int)

# Anzahl WM-Artikel: diskret, Poisson-artig
anzahl_wm = rng.poisson(2.2, N).clip(0, 12)

mannschaften = ["Deutschland","Brasilien","Argentinien","Frankreich",
                "England","Spanien","Portugal","Sonstige"]
lieblings = rng.choice(mannschaften, N, p=[.22,.14,.12,.11,.10,.09,.07,.15])

zahlung = rng.choice(["Kreditkarte","Bankueberweisung","PayPal","Nachnahme"],
                     N, p=[.40,.20,.32,.08])

kaufzeitpunkt = rng.choice(["Vor_WM","Waehrend_WM","Nach_WM"], N, p=[.25,.55,.20])

rabatt_nutzung = np.clip(rng.beta(2, 5, N) * 100, 0, 100).round(1)

# Stammkunde vor WM: ca. 35% waren schon vorher aktiv
stammkunde = rng.binomial(1, 0.35, N)

anzahl_beschwerden = rng.poisson(0.6, N).clip(0, 8)

# --- 2. Churn-Logik: Score aus plausiblen Regeln + Rauschen ---
# Hoeherer Score -> hoehere Abwanderungswahrscheinlichkeit
score = np.zeros(N, dtype=float)

# Stammkunden bleiben eher (starker, aber nicht perfekter Effekt)
score += np.where(stammkunde == 1, -1.3, 0.6)

# Wer NUR waehrend der WM kauft = klassischer Hype-Kaeufer -> wandert eher ab
score += np.where(kaufzeitpunkt == "Waehrend_WM", 0.8, 0.0)
score += np.where(kaufzeitpunkt == "Nach_WM", -0.7, 0.0)  # kauft auch nach WM -> bleibt eher

# Geringe Kaufhaeufigkeit -> hoeheres Risiko
score += (2.0 - kaufhaeufigkeit) * 0.25

# Lange her seit letztem Kauf -> hoeheres Risiko
score += (tage_letzter_kauf - 30) / 60.0

# Hoher WM-Artikel-Anteil bei wenig sonstiger Aktivitaet -> Hype
score += np.where((anzahl_wm >= 3) & (kaufhaeufigkeit < 2), 0.6, 0.0)

# Beschwerden erhoehen Risiko leicht
score += anzahl_beschwerden * 0.15

# Zufallsanteil (Rauschen) -> Klassen nicht perfekt trennbar
score += rng.normal(0, 1.1, N)

# Intercept: verschiebt Basis-Churn-Rate auf realistische ~42%
score += -0.9

# Logistische Transformation -> Wahrscheinlichkeit
prob = 1 / (1 + np.exp(-score))
churn = rng.binomial(1, prob)

df = pd.DataFrame({
    "Kunden_ID": [f"CUST{i+1:04d}" for i in range(N)],
    "Alter": alter,
    "Kaufhaeufigkeit_pro_Monat": kaufhaeufigkeit,
    "Gesamtausgaben_EUR": gesamtausgaben,
    "Tage_seit_letztem_Kauf": tage_letzter_kauf,
    "Anzahl_WM_Artikel": anzahl_wm.astype(float),
    "Lieblings_Nationalmannschaft": lieblings,
    "Zahlungsmethode": zahlung,
    "Kaufzeitpunkt_relativ_WM": kaufzeitpunkt,
    "Rabatt_Nutzung_Pct": rabatt_nutzung,
    "Stammkunde_vor_WM": stammkunde,
    "Anzahl_Beschwerden": anzahl_beschwerden,
    "Churn": churn,
})

# --- 3. Bewusst fehlende Werte (wie im Original) ---
miss_wm = rng.choice(N, size=int(0.05*N), replace=False)
df.loc[miss_wm, "Anzahl_WM_Artikel"] = np.nan
miss_rab = rng.choice(N, size=int(0.06*N), replace=False)
df.loc[miss_rab, "Rabatt_Nutzung_Pct"] = np.nan

df.to_csv("ecommerce_churn_dataset.csv", index=False)
print("Churn-Verteilung:")
print(df["Churn"].value_counts())
print(f"Churn-Rate: {df['Churn'].mean():.2%}")
