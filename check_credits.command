#!/bin/bash
# Shows OpenRouter credit balance and this key's remaining limit (read-only).
cd "$(dirname "$0")"
set -a; [ -f .env ] && . ./.env; set +a
K="${OPENROUTER_API_KEY:-$MEDSIM_OPENROUTER_API_KEY}"
if [ -z "$K" ]; then echo "No OpenRouter key found in .env"; read -n 1 -s -r -p "Press any key to close"; exit 1; fi

python3 - "$K" <<'PY'
import sys, json, urllib.request

def get(path):
    req = urllib.request.Request("https://openrouter.ai/api/v1" + path,
                                 headers={"Authorization": "Bearer " + sys.argv[1]})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["data"]

try:
    c = get("/credits"); k = get("/key")
except Exception as e:
    print("Request failed:", e); sys.exit(1)

bal = c["total_credits"] - c["total_usage"]
print("OpenRouter credits")
print("-" * 30)
print(f"Purchased:        ${c['total_credits']:,.2f}")
print(f"Used:             ${c['total_usage']:,.2f}")
print(f"Account balance:  ${bal:,.2f}" + ("   <-- OUT OF CREDITS" if bal <= 0 else ""))
print()
print("This API key")
print("-" * 30)
lim = k.get("limit")
print(f"Key limit:        " + (f"${lim:,.2f}" if lim is not None else "none"))
rem = k.get("limit_remaining")
if rem is not None:
    print(f"Key remaining:    ${rem:,.2f}")
print(f"Used today:       ${k['usage_daily']:,.2f}")
print(f"Used this week:   ${k['usage_weekly']:,.2f}")
print(f"Used this month:  ${k['usage_monthly']:,.2f}")
PY
echo
read -n 1 -s -r -p "Press any key to close"
