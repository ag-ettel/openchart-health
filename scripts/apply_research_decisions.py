"""Apply web research decisions to the review CSV."""

import csv
from collections import Counter

DECISIONS = {
    # === REVIEW_NAME_MISMATCH (19 entities) ===
    "SKILLED HEALTHCARE LLC": ("KEEP", "OPERATOR", "Genesis acquired Skilled Healthcare Group Feb 2015"),
    "NEWGEN LLC": ("REMOVE", "OPERATOR", "NewGen Health acquired Genesis assets in bankruptcy 2026. Separate operator."),
    "TAFKAR LLC": ("KEEP", "HOLDING_CO", "82.6% director overlap. Likely SavaSeniorCare subsidiary."),
    "ONSHIFT INC": ("REMOVE", "VENDOR", "OnShift is workforce management software. Vendor, not owner."),
    "APERION CARE EXEC HOLDINGS LLC": ("KEEP", "OPERATOR", "Aperion Care is Yosef Meystel operating brand. Confirmed."),
    "BEECAN HEALTH CO LLC": ("REMOVE", "OPERATOR", "Independent operator CA/CO/NM. Merged with Vivage 2023."),
    "CEDARBRIDGE CARE SERVICES LLC": ("KEEP", "OPERATOR", "92.5% director overlap with Rsbrmk. Same family."),
    "COTTONWOOD HEALTHCARE LLC": ("KEEP", "OPERATOR", "93.3% director overlap. Same corporate family."),
    "CORPORATE INTERFACE SERVICES LLC": ("KEEP", "MANAGEMENT_CO", "90% overlap. Rockport Healthcare is CA largest SNF operator."),
    "GUBIN ENTERPRISES LIMITED PARTNERSHIP": ("KEEP", "HOLDING_CO", "85.7% director overlap. Same ownership family."),
    "THE WINTNER LIVING TRUST DATED 7/08/1992": ("KEEP", "FAMILY_TRUST", "85.7% director overlap. Family trust."),
    "ROBIN EISENBERG 2014 FAMILY TRUST": ("KEEP", "FAMILY_TRUST", "85.7% director overlap. Family trust."),
    "JAMES J GIARDINA RVOC LIVING TR RESTATED 07-20-09": ("KEEP", "FAMILY_TRUST", "83.3% director overlap."),
    "HABANERO HOLDING COMPANY LLC": ("KEEP", "HOLDING_CO", "83.3% director overlap with DMD."),
    "ML FAMILY TREE TRUST": ("KEEP", "FAMILY_TRUST", "88.9% director overlap."),
    "ALLIANCE HEALTH GROUP LLC": ("KEEP", "OPERATOR", "ProPublica confirms Zanziper affiliation. 9 NC facilities."),
    "OH 10 HOLDCO LLC": ("KEEP", "HOLDING_CO", "85.7% director overlap with DMD."),
    "CLAYSHIRE LLC": ("KEEP", "OPERATOR", "85.7% director overlap."),
    "UPTOWN FS LLC": ("KEEP", "HOLDING_CO", "91.7% director overlap."),

    # === HIGH: WEAK_LINK ===
    # Hospital districts - separate government entities
    "UVALDE COUNTY HOSPITAL AUTHORITY": ("REMOVE", "GOVERNMENT", "Separate Texas county hospital authority."),
    "CHILDRESS COUNTY HOSPITAL DISTRICT": ("REMOVE", "GOVERNMENT", "Separate Texas county hospital district."),
    "GUNNISON VALLEY HOSPITAL": ("REMOVE", "GOVERNMENT", "Separate Colorado hospital."),
    "RUSH MEMORIAL HOSPITAL": ("REMOVE", "GOVERNMENT", "Separate Indiana hospital."),
    "MEMORIAL HOSPITAL": ("REMOVE", "GOVERNMENT", "Generic name, separate hospital entity."),

    # REIT entities
    "HCP S-H 2014 MEMBER, LLC": ("REMOVE", "REIT", "Healthpeak Properties REIT. Landlord, not operator."),
    "HCP SENIOR HOUSING PROPERTIES, LLC": ("REMOVE", "REIT", "Healthpeak Properties REIT."),
    "HCP S-H OPCO TRS LLC": ("REMOVE", "REIT", "Healthpeak Properties REIT."),
    "HCP S-H SUNRISE OPCO HOLDCO LLC": ("REMOVE", "REIT", "Healthpeak Properties REIT."),
    "CCRC OPCO VENTURES II, LLC": ("REMOVE", "REIT", "Healthpeak Properties REIT."),

    # Separate operators
    "ASBR HOLDINGS LLC": ("REMOVE", "HOLDING_CO", "21% director overlap. Separate."),
    "BRIUS LLC": ("REMOVE", "OPERATOR", "Brius Healthcare separate operator (Shlomo Rechnitz). 81 CA fac."),
    "BRISER HOLDINGS LLC": ("REMOVE", "HOLDING_CO", "37% director overlap. Separate."),
    "CARDON MANAGEMENT COMPANY LLC": ("REMOVE", "MANAGEMENT_CO", "15% director overlap. Separate."),
    "VALLEY STREAM OPERATOR I LLC": ("REMOVE", "OPERATOR", "17% director overlap. Separate."),
    "SDB HOLDINGS": ("REMOVE", "HOLDING_CO", "17% director overlap. Separate."),
    "ASP FL HOLDINGS LLC": ("REMOVE", "HOLDING_CO", "12.5% director overlap. Separate."),
    "ASP FL LLC": ("REMOVE", "HOLDING_CO", "12.5% director overlap. Separate."),
    "EMERALD HEALTHCARE LLC": ("REMOVE", "OPERATOR", "20% director overlap. Separate from Brookdale."),
    "SENIOR CARE EXCELLENCE, LLC": ("REMOVE", "OPERATOR", "33% director overlap. Separate."),
    "PARK NICOLLET HEALTH SERVICES": ("REMOVE", "OPERATOR", "24% director overlap. Separate health system."),
    "MILLENNIUM HEALTH OPERATIONS, LLC": ("REMOVE", "OPERATOR", "36% overlap. Separate."),
    "HIGHPOINT HEALTHCARE LLC": ("REMOVE", "OPERATOR", "33% overlap. Separate."),

    # Banks / vendors / audit firms
    "BOKF,NA": ("REMOVE", "BANK", "Bank of Oklahoma."),
    "BUSEY CORPORATION": ("REMOVE", "BANK", "Busey Corporation is a bank."),
    "OPTIMUMBANK": ("REMOVE", "BANK", "OptimumBank is a bank."),
    "PRIVATE BANCORP INC": ("REMOVE", "BANK", "PrivateBancorp is a bank."),
    "FORVIS MAZARS, LLP": ("REMOVE", "VENDOR", "Accounting/audit firm."),
    "ACCURATE STAFFING LLC": ("REMOVE", "VENDOR", "Staffing agency, not owner."),
    "GOLDEN SNF CONSULTING LLC": ("REMOVE", "MANAGEMENT_CO", "Consulting firm."),
    "ISOMED INC": ("REMOVE", "VENDOR", "Service company."),

    # Small holding/investment entities - weak links
    "STAR PA I HOLDINGS LLC": ("REMOVE", "HOLDING_CO", "11.5% director overlap."),
    "STAR PA I TRUST": ("REMOVE", "FAMILY_TRUST", "13% director overlap."),
    "GREENLEAF VI II INC.": ("REMOVE", "HOLDING_CO", "18% director overlap."),
    "AYSAN TR": ("REMOVE", "FAMILY_TRUST", "11% director overlap."),
    "BUAH TRUST": ("REMOVE", "FAMILY_TRUST", "11% director overlap."),
    "LA2 OPCO MANAGER LLC": ("REMOVE", "MANAGEMENT_CO", "12.5% director overlap."),
    "TULLOCK MANAGEMENT COMPANY": ("REMOVE", "MANAGEMENT_CO", "12% director overlap."),
    "JEK IRRV TR": ("REMOVE", "FAMILY_TRUST", "14% director overlap. Separate."),
    "NMJ IRRV TR": ("REMOVE", "FAMILY_TRUST", "14% director overlap."),
    "NMJ IRRV TRUST": ("REMOVE", "FAMILY_TRUST", "20% director overlap."),
    "JACK RAJCHENBACH FAMILY TRUST": ("REMOVE", "FAMILY_TRUST", "22% director overlap."),
    "MIMI HOLDCO LLC": ("REMOVE", "HOLDING_CO", "26% director overlap."),
    "GLEN HOLDCO LLC": ("REMOVE", "HOLDING_CO", "26% director overlap."),
    "FMI - RIVERLAND LLC": ("REMOVE", "HOLDING_CO", "33% overlap, 3 fac."),
    "FOREST GLEN INVESTMENTS, LLC": ("REMOVE", "INVESTMENT_VEHICLE", "33% overlap. Separate."),
    "CH FH HOLDING LLC": ("REMOVE", "HOLDING_CO", "33% overlap. Separate."),
    "CALISTO HOLDINGS LLC": ("REMOVE", "HOLDING_CO", "33% overlap. Separate from Zanziper."),
    "JOHN C FINLEY TR 05051983": ("REMOVE", "FAMILY_TRUST", "33% overlap. Separate."),

    # Entities with truncated names in CSV
    "IRREVOCABLE GRANTOR TRUST AGREEMENT OF JOHN J SHEE": ("REMOVE", "FAMILY_TRUST", "25% director overlap. Separate."),
    "IRREVOCABLE GRANTOR TRUST AGREEMENT OF MARGARET PH": ("REMOVE", "FAMILY_TRUST", "25% director overlap. Separate."),

    # Confirmed KEEP - Ensign subsidiary
    "FIVE OAKS HEALTHCARE LLC": ("KEEP", "OPERATOR", "CareTrust transferred to Ensign affiliates Jun 2021."),

    # Family trusts that should stay
    "JOE KENNETH NEWTON JR. QSST TRUST": ("KEEP", "FAMILY_TRUST", "Newton family QSST trust. Part of family operator."),
    "KELLY DELANE NEWTON ZIMMERER QSST TRUST": ("KEEP", "FAMILY_TRUST", "Same Newton family."),
    "KRISTI LYNN NEWTON OWENS QSST TRUST": ("KEEP", "FAMILY_TRUST", "Same Newton family."),
    "THE CARMELITE SISTERS FOR THE AGED AND INFIRM": ("KEEP", "OPERATOR", "Religious order operating nursing homes."),
    "HOLLINGER HOLDING COMPANY LLC": ("KEEP", "HOLDING_CO", "Cluster namesake."),
    "LONE STAR ASSETS, FLP": ("KEEP", "FAMILY_TRUST", "40% overlap. Tower Bridge family partnership."),
    "SAIMAA, FLP": ("KEEP", "FAMILY_TRUST", "40% overlap. Tower Bridge family."),
    "TAKI, FLP": ("KEEP", "FAMILY_TRUST", "40% overlap. Tower Bridge family."),

    # === HIGH: no_data (cluster seeds) ===
    "THE ENSIGN GROUP INC": ("KEEP", "OPERATOR", "Cluster namesake. Publicly traded (ENSG)."),
    "PICO AR LLC": ("KEEP", "HOLDING_CO", "Cluster seed."),
    "SGS FAMILY LLC": ("KEEP", "HOLDING_CO", "Cluster seed."),
    "ZCS AR OPCO LLC": ("KEEP", "OPERATOR", "Cluster seed."),
    "TRIO HEALTHCARE LLC": ("KEEP", "OPERATOR", "Cluster seed."),
    "NPNH1 LLC": ("KEEP", "HOLDING_CO", "Cluster seed."),
    "CRHC LLC": ("KEEP", "HOLDING_CO", "Cluster seed."),
    "CENTENNIAL MN TR I": ("KEEP", "FAMILY_TRUST", "Cluster seed."),
    "CHAMBER INC.": ("KEEP", "OPERATOR", "Cluster seed."),
    "GGL RELIANT LLC": ("KEEP", "HOLDING_CO", "Philipson Family cluster."),
    "TPG VII KENTUCKY AIV I LP": ("KEEP", "INVESTMENT_VEHICLE", "TPG Capital fund. Cluster seed."),
}

# Load and apply
with open("data/review_entity_classifications.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

applied = 0
for r in rows:
    name = r["entity_name"]
    decision = DECISIONS.get(name)
    if not decision:
        for dname, d in DECISIONS.items():
            if name.startswith(dname) or dname.startswith(name[:45]):
                decision = d
                break

    if decision:
        action, classification, notes = decision
        r["YOUR_ACTION"] = action
        r["YOUR_CLASSIFICATION"] = classification
        r["YOUR_NOTES"] = notes
        applied += 1

fieldnames = list(rows[0].keys())
with open("data/review_entity_classifications.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Applied {applied} decisions to review CSV")

actions = Counter()
for r in rows:
    a = (r.get("YOUR_ACTION") or "").strip()
    if a:
        actions[a] += 1
print(f"\nAction summary: {dict(actions)}")
print(f"Remaining undecided: {len(rows) - sum(actions.values())}")
