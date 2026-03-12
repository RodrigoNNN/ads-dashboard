#!/usr/bin/env python3
"""
Meta Ads Funnel Dashboard - Data Fetcher
Pulls ad-level performance data from all accounts via Meta Graph API.
Outputs data.json for the dashboard.

Usage: python3 pull_data.py --token YOUR_ACCESS_TOKEN
"""

import json
import subprocess
import argparse
import re
from datetime import datetime, timedelta

# All ad account IDs with custom conversion IDs
ACCOUNTS = {
    "act_270012638593853": {
        "name": "Canada Spas",
        "subscribe_cc": "1277900390927837",
        "schedule_cc": "851146124603750"
    },
    "act_296359479745087": {
        "name": "CDT Central",
        "subscribe_cc": "2420806898376715",
        "schedule_cc": "2318228872017296"
    },
    "act_655866140123386": {
        "name": "Donna Ella",
        "subscribe_cc": "885821961020293",
        "schedule_cc": "2138479693576816"
    },
    "act_916070816315189": {
        "name": "Advanced Beauty",
        "subscribe_cc": "1516441993821197",
        "schedule_cc": "1551751015889447"
    },
    "act_841143877401548": {
        "name": "East Coast FTB",
        "subscribe_cc": "1821893908501174",
        "schedule_cc": "2717629371910954"
    },
    "act_374188775345683": {
        "name": "West Coast FTB",
        "subscribe_cc": "27117001434556011",
        "schedule_cc": "1009075661780620"
    },
    "act_690215289018409": {
        "name": "West Coast Spas",
        "subscribe_cc": "973746015084658",
        "schedule_cc": "1255440422849666"
    },
    "act_610012775096741": {
        "name": "Skin Totale",
        "subscribe_cc": "917438154482060",
        "schedule_cc": "926006056462124"
    },
    "act_927143367886771": {
        "name": "Florida Spas",
        "subscribe_cc": "2155894761621696",
        "schedule_cc": "926604143456361"
    },
    "act_770943643874369": {
        "name": "East Coast Spas",
        "subscribe_cc": "1635052164335205",
        "schedule_cc": "944692684685833"
    },
    "act_1120596088461407": {
        "name": "NC Spas",
        "subscribe_cc": "878596171672567",
        "schedule_cc": "1652406652444468"
    },
    "act_933674888565470": {
        "name": "ADV General",
        "subscribe_cc": "1451258336648943",
        "schedule_cc": "1238941971720114"
    },
    "act_2022622814575315": {
        "name": "Skin Totale SJ",
        "subscribe_cc": "1458131932615974",
        "schedule_cc": "4173758389543106"
    },
    "act_637200935381904": {
        "name": "Solei Beauty",
        "subscribe_cc": "",
        "schedule_cc": ""
    },
}


def extract_client(campaign_name):
    """Extract client name from campaign. Format: '... | Client Name | Location | ...'"""
    parts = campaign_name.split("|")
    if len(parts) >= 2:
        return parts[1].strip()
    return campaign_name[:40]


def fetch_ad_statuses(account_id, token):
    """Fetch effective_status for all ads in an account."""
    cmd = [
        "curl", "-s", "-G",
        f"https://graph.facebook.com/v19.0/{account_id}/ads",
        "--data-urlencode", "fields=id,name,effective_status,campaign{effective_status}",
        "--data-urlencode", "limit=500",
        "--data-urlencode", f"access_token={token}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    statuses = {}
    for ad in data.get("data", []):
        ad_name = ad.get("name", "")
        statuses[ad_name] = {
            "ad_status": ad.get("effective_status", "UNKNOWN"),
            "campaign_status": ad.get("campaign", {}).get("effective_status", "UNKNOWN"),
        }
    return statuses


def fetch_account_data(account_id, account_info, token, since, until):
    """Fetch ad-level insights for one account."""
    # First get ad statuses
    statuses = fetch_ad_statuses(account_id, token)

    cmd = [
        "curl", "-s", "-G",
        f"https://graph.facebook.com/v19.0/{account_id}/insights",
        "--data-urlencode", "fields=ad_name,campaign_name,spend,actions,cost_per_action_type",
        "--data-urlencode", f'time_range={{"since":"{since}","until":"{until}"}}',
        "--data-urlencode", "level=ad",
        "--data-urlencode", "limit=500",
        "--data-urlencode", f"access_token={token}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  ⚠️  Failed to parse response for {account_info['name']}")
        return []

    if "error" in data:
        print(f"  ⚠️  API error for {account_info['name']}: {data['error'].get('message', '?')}")
        return []

    ads = []
    sub_cc = account_info["subscribe_cc"]
    sch_cc = account_info["schedule_cc"]

    for row in data.get("data", []):
        ad_name = row.get("ad_name", "?")
        campaign_name = row.get("campaign_name", "?")
        spend = float(row.get("spend", 0))

        if spend == 0:
            continue

        # Parse actions
        actions = row.get("actions", [])
        leads = 0
        purchases = 0
        complete_registrations = 0
        schedules = 0
        arrivals = 0

        for a in actions:
            at = a.get("action_type", "")
            val = int(float(a.get("value", 0)))

            if at == "offsite_conversion.fb_pixel_lead":
                leads = val
            elif at == "offsite_conversion.fb_pixel_purchase":
                purchases = val
            elif at == "offsite_conversion.fb_pixel_complete_registration":
                complete_registrations = val
            elif sub_cc and at == f"offsite_conversion.custom.{sub_cc}":
                arrivals = val
            elif sch_cc and at == f"offsite_conversion.custom.{sch_cc}":
                schedules = val

        # Calculate costs
        cpl = round(spend / leads, 2) if leads > 0 else None
        cost_purchase = round(spend / purchases, 2) if purchases > 0 else None
        cost_cr = round(spend / complete_registrations, 2) if complete_registrations > 0 else None
        cost_schedule = round(spend / schedules, 2) if schedules > 0 else None
        cost_arrival = round(spend / arrivals, 2) if arrivals > 0 else None

        # Get status from lookup
        ad_status_info = statuses.get(ad_name, {})
        ad_status = ad_status_info.get("ad_status", "UNKNOWN")
        campaign_status = ad_status_info.get("campaign_status", "UNKNOWN")

        ads.append({
            "account": account_info["name"],
            "client": extract_client(campaign_name),
            "campaign": campaign_name,
            "campaign_status": campaign_status,
            "ad": ad_name,
            "ad_status": ad_status,
            "spend": round(spend, 2),
            "leads": leads,
            "cpl": cpl,
            "purchases": purchases,
            "cost_purchase": cost_purchase,
            "complete_registrations": complete_registrations,
            "cost_cr": cost_cr,
            "schedules": schedules,
            "cost_schedule": cost_schedule,
            "arrivals": arrivals,
            "cost_arrival": cost_arrival,
        })

    return ads


def main():
    parser = argparse.ArgumentParser(description="Pull Meta Ads data for dashboard")
    parser.add_argument("--token", required=True, help="Meta Graph API access token")
    parser.add_argument("--days", type=int, default=30, help="Number of days to look back (default: 30)")
    args = parser.parse_args()

    until = datetime.now().strftime("%Y-%m-%d")
    since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    print(f"📊 Pulling ad data from {since} to {until}")
    print(f"   Querying {len(ACCOUNTS)} accounts...\n")

    all_ads = []

    for account_id, info in ACCOUNTS.items():
        print(f"  → {info['name']} ({account_id})...", end=" ", flush=True)
        ads = fetch_account_data(account_id, info, args.token, since, until)
        print(f"{len(ads)} ads")
        all_ads.extend(ads)

    # Sort by spend descending
    all_ads.sort(key=lambda x: x["spend"], reverse=True)

    output = {
        "updated": datetime.now().isoformat(),
        "date_range": {"since": since, "until": until},
        "total_ads": len(all_ads),
        "total_spend": round(sum(a["spend"] for a in all_ads), 2),
        "total_leads": sum(a["leads"] for a in all_ads),
        "total_arrivals": sum(a["arrivals"] for a in all_ads),
        "ads": all_ads,
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Done! {len(all_ads)} ads saved to data.json")
    print(f"   Total spend: ${output['total_spend']:,.2f}")
    print(f"   Total leads: {output['total_leads']}")
    print(f"   Total arrivals: {output['total_arrivals']}")


if __name__ == "__main__":
    main()
