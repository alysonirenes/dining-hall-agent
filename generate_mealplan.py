#!/usr/bin/env python3
"""
Dining Hall Meal Plan Generator
Customized for: 5'9", 120 lb, 20 y/o woman looking to gain weight.
Rules:
- 2 meals/day (breakfast, ~5pm).
- Uses daily Nutrislice menu.
- Always includes: salad bar (~300 kcal), deli sandwich (~600 kcal), yogurt (~150 kcal),
  pizza (~350 kcal), chicken tenders (~400 kcal), fries (~300 kcal), grilled chicken (~250 kcal),
  pasta + sauce (~500 kcal).
- Excludes fish.
- Goal: high calorie plan.
"""

import requests, re, argparse, datetime, sys
from urllib.parse import urlparse

# Always-available foods (with calorie estimates)
ALWAYS_AVAILABLE = [
    {"name": "Salad bar", "calories": 300},
    {"name": "Deli sandwich", "calories": 600},
    {"name": "Yogurt", "calories": 150},
    {"name": "Pizza", "calories": 350},
    {"name": "Chicken tenders", "calories": 400},
    {"name": "French fries", "calories": 300},
    {"name": "Grilled chicken", "calories": 250},
    {"name": "Pasta with sauce", "calories": 500},
]

def find_api_urls(page_url):
    r = requests.get(page_url, timeout=15)
    html = r.text
    return re.findall(r'https?://[A-Za-z0-9\.-]+\.api\.nutrislice\.com/menu/api/weeks/[^"\']+', html)

def guess_api_by_slug(page_url):
    p = urlparse(page_url)
    host = p.hostname
    if not host: return []
    district = host.split('.')[0]
    m = re.search(r'/menu/([^/?#]+)', p.path)
    if not m: return []
    school_slug = m.group(1)
    today = datetime.date.today()
    y,mn,d = today.year, today.month, today.day
    return [
        f'https://{district}.api.nutrislice.com/menu/api/weeks/school/{school_slug}/menu-type/{meal}/{y}/{mn}/{d}/?format=json'
        for meal in ['breakfast','lunch','dinner']
    ]

def fetch_json(candidates):
    for url in candidates:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code==200:
                return r.json()
        except: continue
    raise RuntimeError("Could not fetch Nutrislice JSON. Try copying the XHR URL from browser DevTools.")

def extract_items(week_json):
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    items=[]
    days = week_json.get('days') or week_json.get('menu_days') or []
    for d in days:
        if d.get('date') == today_str:
            for mi in d.get('menu_items', []):
                food = mi.get('food') or {}
                name = (food.get('name') or mi.get('text') or 'Unknown').strip()
                # Skip fish
                if "fish" in name.lower() or "salmon" in name.lower() or "tilapia" in name.lower():
                    continue
                cals = None
                rounded = food.get('rounded_nutrition_info') or {}
                if rounded.get('calories'): cals = rounded['calories']
                elif mi.get('aggregated_data', {}).get('calories'):
                    cals = mi['aggregated_data']['calories']
                items.append({"name": name, "calories": float(cals) if cals else 250})
    return items

def build_plan(items):
    # Merge in always-available foods
    items = items + ALWAYS_AVAILABLE
    # Sort high → low calorie
    items_sorted = sorted(items, key=lambda x: x['calories'], reverse=True)

    plan = {"Breakfast": [], "Dinner": []}
    used=set()

    for meal in plan:
        meal_total=0
        while meal_total < 1200 and len(plan[meal])<6:  # aim for ~1200+ kcal per meal
            for it in items_sorted:
                if it['name'] in used: continue
                plan[meal].append(it)
                used.add(it['name'])
                meal_total+=it['calories']
                break
    return plan

def format_plan(plan):
    out=[f"# Meal Plan for {datetime.date.today().isoformat()}\n"]
    total=0
    for meal, items in plan.items():
        out.append(f"## {meal}\n")
        subtotal=0
        for it in items:
            out.append(f"- {it['name']} — {int(it['calories'])} kcal\n")
            subtotal+=it['calories']
        out.append(f"**{meal} subtotal: {int(subtotal)} kcal**\n\n")
        total+=subtotal
    out.append(f"**Daily Total: {int(total)} kcal**\n")
    return "\n".join(out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-url", required=True, help="Nutrislice menu page URL")
    args = parser.parse_args()

    candidates = find_api_urls(args.page_url) or guess_api_by_slug(args.page_url)
    data = fetch_json(candidates)
    items = extract_items(data)
    plan = build_plan(items)
    md = format_plan(plan)
    outname=f"mealplan_{datetime.date.today().isoformat()}.md"
    with open(outname,"w",encoding="utf-8") as f: f.write(md)
    print(md)

if __name__=="__main__":
    main()
