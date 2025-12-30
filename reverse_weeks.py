#!/usr/bin/env python3
"""
Reverse the week numbering in the training plan.
Convert from countdown (18, 17...0, -1...) to count-up (1, 2, 3...19, 20...)
"""

import yaml

# Read the plan
with open('plans/nyc_marathon_2026.yaml', 'r') as f:
    plan = yaml.safe_load(f)

# Reverse the week numbers
# Old: 18, 17, 16... 0, -1, -2, -3, -4, -5
# New: 1, 2, 3... 19, 20, 21, 22, 23, 24
# Formula: new_week = 19 - old_week

for week in plan['weeks']:
    old_week = week['week']
    new_week = 19 - old_week
    week['week'] = new_week

    # Update weeks_to_goal if it exists
    if 'weeks_to_goal' in week:
        # weeks_to_goal should now be: total_weeks - current_week + 1
        # For week 1: 19 - 1 = 18 weeks to goal
        # For week 18: 19 - 18 = 1 week to goal
        # For week 19 (race): 19 - 19 = 0 weeks to goal
        week['weeks_to_goal'] = 19 - new_week

    print(f"Changed week {old_week} → week {new_week} (weeks to goal: {week.get('weeks_to_goal', 'N/A')})")

# Write back
with open('plans/nyc_marathon_2026.yaml', 'w') as f:
    yaml.dump(plan, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

print("\n✓ Week numbering reversed successfully!")
print("Week 1 is now the first week of training (18 weeks before race)")
print("Week 19 is race week")
