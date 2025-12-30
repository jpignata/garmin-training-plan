#!/usr/bin/env python3
"""
Upload a test workout and download it back to see Garmin's format
"""

import json
import os
from sync_garmin import GarminTrainingPlanSync
from garmin_workout_builder import WorkoutBuilder
from datetime import datetime
import garth

# Authenticate
email = os.getenv('GARMIN_EMAIL')
password = os.getenv('GARMIN_PASSWORD')

tokenstore_dir = os.path.expanduser("~/.garminconnect")
if os.path.exists(tokenstore_dir):
    garth.resume(tokenstore_dir)
else:
    garth.login(email, password, prompt_mfa=lambda: input("Enter MFA code: ").strip())
    garth.save(tokenstore_dir)

from garminconnect import Garmin
api = Garmin()
api.garth = garth.client
api.username = email

print("Fetching first uploaded workout...")
workouts = api.get_workouts(start=0, limit=5)

if workouts:
    workout = workouts[0] if isinstance(workouts, list) else workouts
    workout_id = workout.get('workoutId')
    workout_name = workout.get('workoutName', 'Unknown')

    print(f"\nWorkout: {workout_name}")
    print(f"ID: {workout_id}")

    print("\nFetching full workout details...")
    full_workout = api.get_workout_by_id(workout_id)

    print("\n=== FULL WORKOUT JSON ===\n")
    print(json.dumps(full_workout, indent=2))

    # Save to file for inspection
    with open('downloaded_workout.json', 'w') as f:
        json.dumps(full_workout, f, indent=2)

    print("\n\nSaved to downloaded_workout.json")

    # Show target info
    print("\n=== TARGET INFO FROM GARMIN ===")
    for segment in full_workout.get('workoutSegments', []):
        for step in segment.get('workoutSteps', []):
            if step.get('type') == 'ExecutableStepDTO':
                print(f"\nStep {step.get('stepOrder')}: {step.get('stepType', {}).get('stepTypeKey')}")
                print(f"  Target Type: {step.get('targetType', {})}")
                if 'targetValueOne' in step:
                    print(f"  Target Value One: {step['targetValueOne']}")
                if 'targetValueTwo' in step:
                    print(f"  Target Value Two: {step['targetValueTwo']}")
else:
    print("No workouts found!")
