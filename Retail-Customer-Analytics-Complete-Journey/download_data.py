"""
download_data.py
Lädt die benötigten Tabellen des 84.51° "Complete Journey 2.0"-Datensatzes
(Lizenz: CC0) aus dem R-Paket completejourney nach ./data/.
"""
import pathlib
import urllib.request

BASE = "https://github.com/bradleyboehmke/completejourney/raw/master/data/"
FILES = ["transactions.rds", "demographics.rda", "products.rda",
         "campaigns.rda", "campaign_descriptions.rda", "coupon_redemptions.rda"]

out = pathlib.Path("data")
out.mkdir(exist_ok=True)
for name in FILES:
    target = out / name
    if target.exists():
        print("vorhanden:", name)
        continue
    print("lade:", name)
    urllib.request.urlretrieve(BASE + name, target)
print("Fertig.")
