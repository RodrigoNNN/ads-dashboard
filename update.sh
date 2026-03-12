#!/bin/bash
# Weekly data update script
# Usage: ./update.sh YOUR_META_ACCESS_TOKEN
# Run every Thursday morning before the team meeting

set -e

if [ -z "$1" ]; then
    echo "❌ Usage: ./update.sh YOUR_META_ACCESS_TOKEN"
    echo "   Get a fresh token from Meta Business Suite → Graph API Explorer"
    exit 1
fi

TOKEN="$1"
DAYS="${2:-30}"

echo "🔄 Updating dashboard data..."
python3 pull_data.py --token "$TOKEN" --days "$DAYS"

echo ""
echo "📤 Pushing to GitHub..."
git add data.json
git commit -m "Weekly data update $(date +%Y-%m-%d)"
git push

echo ""
echo "✅ Done! Vercel will auto-deploy in ~30 seconds."
echo "   Dashboard: https://ads-dashboard.vercel.app"
