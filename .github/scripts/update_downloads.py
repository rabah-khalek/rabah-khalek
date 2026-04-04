import jwt, time, requests, gzip, io, csv, json, os
from datetime import date

KEY_ID      = os.environ["ASC_KEY_ID"]
ISSUER_ID   = os.environ["ASC_ISSUER_ID"]
PRIVATE_KEY = os.environ["ASC_PRIVATE_KEY"]
VENDOR      = os.environ["VENDOR_NUMBER"]
GIST_ID     = "40ee02d1099cf357f13d3f0fdeae2d83"
GIST_TOKEN  = os.environ["GIST_TOKEN"]

APP_IDS = {
    "6754346516": "zetanotes",
    "6754805460": "zetareps",
}

def make_token():
    now = int(time.time())
    return jwt.encode(
        {"iss": ISSUER_ID, "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"},
        PRIVATE_KEY,
        algorithm="ES256",
        headers={"kid": KEY_ID},
    )

def fetch_report(token, frequency, report_date):
    r = requests.get(
        "https://api.appstoreconnect.apple.com/v1/salesReports",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "filter[vendorNumber]": VENDOR,
            "filter[reportType]": "SALES",
            "filter[reportSubType]": "SUMMARY",
            "filter[frequency]": frequency,
            "filter[reportDate]": report_date,
        },
    )
    if r.status_code == 200:
        return gzip.decompress(r.content).decode("utf-8")
    return None

def sum_units(tsv, app_ids):
    counts = {v: 0 for v in app_ids.values()}
    reader = csv.DictReader(io.StringIO(tsv), delimiter="\t")
    for row in reader:
        apple_id = row.get("Apple Identifier", "").strip()
        if apple_id in app_ids:
            try:
                counts[app_ids[apple_id]] += int(float(row.get("Units", 0)))
            except ValueError:
                pass
    return counts

token = make_token()
totals = {"zetanotes": 0, "zetareps": 0}

current_year = date.today().year
for year in range(2024, current_year):
    tsv = fetch_report(token, "YEARLY", str(year))
    if tsv:
        for k, v in sum_units(tsv, APP_IDS).items():
            totals[k] += v

current_month = date.today().month
for month in range(1, current_month):
    tsv = fetch_report(token, "MONTHLY", f"{current_year}-{month:02d}")
    if tsv:
        for k, v in sum_units(tsv, APP_IDS).items():
            totals[k] += v

print("Totals:", totals)

resp = requests.patch(
    f"https://api.github.com/gists/{GIST_ID}",
    headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
    json={"files": {"zetadownloads.json": {"content": json.dumps(totals)}}},
)
resp.raise_for_status()
print("Gist updated.")
