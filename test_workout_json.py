#!/usr/bin/env python3
"""Test workout JSON generation"""

import yaml
import json
from datetime import datetime
from garmin_workout_builder import WorkoutBuilder

# Load the plan
with open('plans/nyc_marathon_2026.yaml', 'r') as f:
    plan = yaml.safe_load(f)

# Get a workout with pace targets
week_1 = plan['weeks'][0]  # First week
tuesday_workout = week_1['workouts']['tuesday']

print("Tuesday Workout from Week 1:")
print(f"Type: {tuesday_workout['type']}")
print(f"Description: {tuesday_workout['description']}")
print(f"\nStructure:")
print(json.dumps(tuesday_workout.get('structure'), indent=2))

# Build the workout
builder = WorkoutBuilder(plan['paces'])
workout_json = builder.build_workout_from_yaml(
    tuesday_workout,
    datetime(2026, 6, 30),
    1,
    'tuesday'
)

print("\n\n=== GENERATED WORKOUT JSON ===\n")
print(json.dumps(workout_json, indent=2))

# Show the target info specifically
print("\n\n=== TARGET INFO ===")
for step in workout_json['workoutSegments'][0]['workoutSteps']:
    if 'targetType' in step:
        print(f"\nStep Order {step.get('stepOrder')}:")
        print(f"  Step Type: {step.get('stepType', {}).get('stepTypeKey')}")
        print(f"  Target Type ID: {step['targetType'].get('workoutTargetTypeId')}")
        print(f"  Target Type Key: {step['targetType'].get('workoutTargetTypeKey')}")
        if 'targetValueOne' in step['targetType']:
            print(f"  Target Value One: {step['targetType']['targetValueOne']}")
            print(f"  Target Value Two: {step['targetType']['targetValueTwo']}")
