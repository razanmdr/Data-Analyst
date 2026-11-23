"""
analysis.py
Customer Churn Prediction - WM-Sportartikel-Shop
Mochammad Dary Razan (E-Commerce)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)


# 1. Daten laden und bereinigen
df = pd.read_csv("ecommerce_churn_dataset.csv")
print("Datensatz geladen:", df.shape)
print("\nFehlende Werte:")
print(df.isna().sum()[df.isna().sum() > 0])

# Fehlende Werte mit dem Median auffuellen
df["Anzahl_WM_Artikel"] = df["Anzahl_WM_Artikel"].fillna(df["Anzahl_WM_Artikel"].median())
df["Rabatt_Nutzung_Pct"] = df["Rabatt_Nutzung_Pct"].fillna(df["Rabatt_Nutzung_Pct"].median())

# Positive Klasse = Kaeufer (Kunde kauft weiter, Churn=0)
df["Klasse"] = ["Kaeufer" if c == 0 else "Nichtkaeufer" for c in df.Churn]

df_kaeufer = df[df.Klasse == "Kaeufer"]
df_nichtkaeufer = df[df.Klasse == "Nichtkaeufer"]


# 2. Deskriptive Statistik und Grafiken
print("\n--- Deskriptive Statistik ---")
print(df.describe().round(2))

# Boxplots
merkmale = ["Kaufhaeufigkeit_pro_Monat", "Tage_seit_letztem_Kauf",
            "Gesamtausgaben_EUR", "Alter"]
fig, axes = plt.subplots(2, 2, figsize=(11, 8))
for ax, spalte in zip(axes.ravel(), merkmale):
    p = ax.boxplot([df_kaeufer[spalte], df_nichtkaeufer[spalte]], patch_artist=True)
    farben = ["lightgreen", "orange"]
    for i, patch in enumerate(p["boxes"]):
        patch.set_facecolor(farben[i])
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["Kaeufer", "Nichtkaeufer"])
    ax.set_title(spalte)
plt.tight_layout()
plt.savefig("images/boxplots.png")
plt.close()

# Histogramm
plt.hist(df_kaeufer.Tage_seit_letztem_Kauf, bins=20, alpha=0.6, label="Kaeufer", color="lightgreen")
plt.hist(df_nichtkaeufer.Tage_seit_letztem_Kauf, bins=20, alpha=0.6, label="Nichtkaeufer", color="orange")
plt.xlabel("Tage seit letztem Kauf")
plt.ylabel("Haeufigkeit")
plt.legend()
plt.savefig("images/histogramm.png")
plt.close()

# Balkendiagramm
kreuztabelle = pd.crosstab(df.Kaufzeitpunkt_relativ_WM, df.Klasse)
kreuztabelle.plot(kind="bar", color=["lightgreen", "orange"])
plt.xlabel("Kaufzeitpunkt relativ zur WM")
plt.tight_layout()
plt.savefig("images/balkendiagramm.png")
plt.close()
print("\nGrafiken gespeichert.")


# 3. Signifikanztests
print("\n--- T-Tests (numerische Merkmale) ---")
numerisch = ["Alter", "Kaufhaeufigkeit_pro_Monat", "Gesamtausgaben_EUR",
             "Tage_seit_letztem_Kauf", "Anzahl_WM_Artikel",
             "Rabatt_Nutzung_Pct", "Stammkunde_vor_WM", "Anzahl_Beschwerden"]
for spalte in numerisch:
    t, p = stats.ttest_ind(df_kaeufer[spalte], df_nichtkaeufer[spalte], equal_var=False)
    print(f"{spalte:28s}: p = {p:.4f}", "signifikant" if p < 0.05 else "nicht-signifikant")

print("\n--- Chi-Quadrat-Tests (kategorische Merkmale) ---")
kategorisch = ["Lieblings_Nationalmannschaft", "Zahlungsmethode", "Kaufzeitpunkt_relativ_WM"]
for spalte in kategorisch:
    kt = pd.crosstab(df[spalte], df.Klasse)
    chi2, p, dof, ew = stats.chi2_contingency(kt)
    print(f"{spalte:28s}: p = {p:.4f}", "signifikant" if p < 0.05 else "nicht-signifikant")


# 4. Modelle trainieren und evaluieren (10-Fold Cross-Validation)
# cross_val_predict teilt die Daten in 10 Folds und trainiert pro Modell 10 Modelle:
# jedes Fold dient einmal als Testmenge, die uebrigen neun als Trainingsmenge.
# Bei sechs Modellen ergeben sich damit insgesamt 60 Trainingsdurchlaeufe.
X = df.drop(columns=["Churn", "Klasse", "Kunden_ID"])
X = pd.get_dummies(X)
y = df.Klasse

from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import confusion_matrix

modelle = {
    "Logistische Regression": LogisticRegression(max_iter=5000),
    "Naive Bayes": GaussianNB(),
    "Entscheidungsbaum": DecisionTreeClassifier(random_state=1),
    "k-Nearest-Neighbors": KNeighborsClassifier(),
    "Neuronales Netz": MLPClassifier(random_state=1, max_iter=1000),
    "Random Forest": RandomForestClassifier(random_state=1),
}

print("\n--- Modell-Evaluation (Sicht: Kaeufer) ---")
print(f"{'Modell':24s} {'Accuracy':>9s} {'TPR':>6s} {'FPR':>6s} {'Precision':>10s}")

confusion_matrizen = {}
for name, model in modelle.items():
    y_pred = cross_val_predict(model, X, y, cv=10)
    cm = confusion_matrix(y, y_pred, labels=["Kaeufer", "Nichtkaeufer"])
    confusion_matrizen[name] = cm

    tp = cm[0, 0]   # Kaeufer richtig erkannt
    fn = cm[0, 1]   # Kaeufer als Nichtkaeufer eingestuft
    fp = cm[1, 0]   # Nichtkaeufer als Kaeufer eingestuft
    tn = cm[1, 1]   # Nichtkaeufer richtig erkannt

    acc = (tp + tn) / cm.sum()
    tpr = tp / (tp + fn)
    fpr = fp / (fp + tn)
    precision = tp / (tp + fp)
    print(f"{name:24s} {acc:9.3f} {tpr:6.2f} {fpr:6.2f} {precision:10.2f}")


# 5. Oekonomische Betrachtung (Kostenmatrix)
gTP = 150   # Kaeufer erkannt, kauft ohne Rabatt
gFN = 138   # Kaeufer nicht erkannt, erhaelt Rabatt und kauft (150-12)
gFP = 0     # Nichtkaeufer als Kaeufer eingestuft, Rabattcode nicht eingeloest
gTN = 63    # Nichtkaeufer richtig erkannt

print("\n--- Oekonomische Betrachtung ---")
print(f"Kostenmatrix: TP={gTP}  FN={gFN}  FP={gFP}  TN={gTN} (EUR)")
print(f"{'Modell':24s} {'Gewinn':>10s}")

for name, cm in confusion_matrizen.items():
    gewinn = cm[0, 0]*gTP + cm[0, 1]*gFN + cm[1, 0]*gFP + cm[1, 1]*gTN
    print(f"{name:24s} {gewinn:10.0f}")


# 6. Oekonomische Konfiguration (Threshold-Optimierung)
from sklearn.metrics import roc_curve

model = LogisticRegression(max_iter=5000)
model.fit(X, y)
y_score = model.predict_proba(X)[:, 0]   # Wahrscheinlichkeit fuer "Kaeufer"

fpr, tpr, thresholds = roc_curve(y, y_score, pos_label="Kaeufer")

nP = len(df_kaeufer)        # Anzahl Kaeufer
nN = len(df_nichtkaeufer)   # Anzahl Nichtkaeufer

roc = pd.DataFrame({"Threshold": thresholds, "FPR": fpr, "TPR": tpr})
roc["Gewinn"] = [row.TPR*gTP*nP +
                 (1-row.TPR)*gFN*nP +
                 row.FPR*gFP*nN +
                 (1-row.FPR)*gTN*nN
                 for index, row in roc.iterrows()]

best = roc[roc.Gewinn == roc.Gewinn.max()]
print("\n--- Threshold-Optimierung (Logistische Regression) ---")
print("Optimaler Threshold:", round(best.Threshold.iloc[0], 2))
print("Maximaler Gewinn:", round(best.Gewinn.iloc[0]))

plt.plot(roc.Threshold, roc.Gewinn)
plt.xlabel("Threshold")
plt.ylabel("Gewinn (EUR)")
plt.title("Gewinn in Abhaengigkeit vom Threshold")
plt.savefig("images/threshold.png")
plt.close()


# 7. Bonus: Clusteranalyse
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score

X_cluster = df[["Kaufhaeufigkeit_pro_Monat", "Gesamtausgaben_EUR",
                "Tage_seit_letztem_Kauf", "Anzahl_WM_Artikel"]]

# Standardisierung: alle Merkmale auf Mittelwert 0 und Standardabweichung 1
# (noetig, da KMeans sonst von Merkmalen mit grossen Zahlen dominiert wird)
X_cluster = (X_cluster - X_cluster.mean()) / X_cluster.std()

print("\n--- Bonus: Clusteranalyse ---")
model = KMeans(n_clusters=3, random_state=1, n_init=10)
model.fit(X_cluster)
df["Cluster"] = model.labels_

print("Calinski-Harabasz-Score:", round(calinski_harabasz_score(X_cluster, model.labels_), 2))
print("\nCluster-Profile (Mittelwerte in Originaleinheiten):")
print(df.groupby("Cluster")[["Kaufhaeufigkeit_pro_Monat", "Gesamtausgaben_EUR",
                             "Tage_seit_letztem_Kauf", "Anzahl_WM_Artikel"]].mean().round(2))
print("\nChurn-Rate pro Cluster:")
print(df.groupby("Cluster").Churn.mean().round(2))

plt.scatter(df.Gesamtausgaben_EUR, df.Kaufhaeufigkeit_pro_Monat, c=df.Cluster)
plt.xlabel("Gesamtausgaben (EUR)")
plt.ylabel("Kaufhaeufigkeit pro Monat")
plt.title("Kundensegmente (K-Means)")
plt.savefig("images/cluster.png")
plt.close()

print("\nFertig.")
