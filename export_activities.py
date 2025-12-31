#!/usr/bin/env python3
"""
Export recent Garmin activities for training analysis with Claude.

Fetches activities from Garmin Connect and exports to markdown format
with all relevant details: splits, HR data, paces, and training metrics.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from garminconnect import Garmin
import garth


def authenticate():
    """Authenticate with Garmin Connect"""
    email = os.getenv('GARMIN_EMAIL')
    password = os.getenv('GARMIN_PASSWORD')

    if not email or not password:
        print("Error: GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set")
        sys.exit(1)

    tokenstore_dir = os.path.expanduser("~/.garminconnect")

    try:
        if os.path.exists(tokenstore_dir):
            garth.resume(tokenstore_dir)
        else:
            garth.login(email, password, prompt_mfa=lambda: input("Enter MFA code: ").strip())
            garth.save(tokenstore_dir)

        api = Garmin()
        api.garth = garth.client
        api.username = email

        return api

    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


def format_duration(seconds):
    """Convert seconds to HH:MM:SS or MM:SS format"""
    if not seconds:
        return "0:00"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_pace(meters_per_second):
    """Convert m/s to min:sec per mile"""
    if not meters_per_second or meters_per_second == 0:
        return "N/A"

    # m/s to miles per hour
    mph = meters_per_second * 2.23694
    if mph == 0:
        return "N/A"

    min_per_mile = 60 / mph
    minutes = int(min_per_mile)
    seconds = int((min_per_mile - minutes) * 60)

    return f"{minutes}:{seconds:02d}"


def get_recent_activities(api, days=15):
    """Fetch activities from the last N days"""
    print(f"Fetching activities from last {days} days...")

    try:
        # Get up to 100 activities (should cover the time period)
        activities = api.get_activities(0, 100)

        cutoff_date = datetime.now() - timedelta(days=days)
        recent = []

        for activity in activities:
            # Parse activity date
            start_time = activity.get('startTimeLocal', '')
            if not start_time:
                continue

            activity_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

            if activity_date >= cutoff_date:
                recent.append(activity)

        return sorted(recent, key=lambda x: x.get('startTimeLocal', ''), reverse=True)

    except Exception as e:
        print(f"Failed to fetch activities: {e}")
        return []


def get_activity_splits(api, activity_id):
    """Get lap/split data for an activity"""
    try:
        splits = api.get_activity_splits(activity_id)
        return splits.get('lapDTOs', [])
    except Exception as e:
        print(f"  Warning: Could not fetch splits for activity {activity_id}: {e}")
        return []


def export_to_markdown(api, activities, output_file):
    """Export activities to markdown format"""

    with open(output_file, 'w') as f:
        f.write("# Training Log Export\n\n")
        f.write(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Activities:** {len(activities)}\n\n")
        f.write("---\n\n")

        for i, activity in enumerate(activities, 1):
            activity_id = activity.get('activityId')
            activity_name = activity.get('activityName', 'Unnamed Activity')
            activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')

            print(f"Processing {i}/{len(activities)}: {activity_name}")

            # Parse date
            start_time = activity.get('startTimeLocal', '')
            if start_time:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d')
                day_str = dt.strftime('%A')
            else:
                date_str = "Unknown"
                day_str = ""

            # Write activity header
            f.write(f"## {date_str} ({day_str}) - {activity_name}\n\n")
            f.write(f"**Type:** {activity_type}\n\n")

            # Summary metrics
            f.write("### Summary\n\n")

            distance_mi = activity.get('distance', 0) / 1609.34
            f.write(f"- **Distance:** {distance_mi:.2f} miles\n")

            duration = activity.get('duration')
            moving_duration = activity.get('movingDuration')
            if duration:
                f.write(f"- **Duration:** {format_duration(duration)}")
                if moving_duration and moving_duration != duration:
                    f.write(f" (moving: {format_duration(moving_duration)})")
                f.write("\n")

            avg_speed = activity.get('averageSpeed')
            if avg_speed:
                f.write(f"- **Average Pace:** {format_pace(avg_speed)}/mile\n")

            avg_hr = activity.get('averageHR')
            max_hr = activity.get('maxHR')
            if avg_hr:
                f.write(f"- **Heart Rate:** {int(avg_hr)} bpm avg")
                if max_hr:
                    f.write(f", {int(max_hr)} bpm max")
                f.write("\n")

            cadence = activity.get('averageRunningCadenceInStepsPerMinute')
            if cadence:
                f.write(f"- **Cadence:** {int(cadence)} spm\n")

            elevation = activity.get('elevationGain')
            if elevation:
                elevation_ft = elevation * 3.28084
                f.write(f"- **Elevation Gain:** {int(elevation_ft)} ft\n")

            calories = activity.get('calories')
            if calories:
                f.write(f"- **Calories:** {int(calories)}\n")

            f.write("\n")

            # Get and display splits
            splits = get_activity_splits(api, activity_id)

            if splits and len(splits) > 0:
                f.write("### Splits\n\n")
                f.write("| Split | Distance | Time | Pace | Avg HR | Max HR |\n")
                f.write("|-------|----------|------|------|--------|--------|\n")

                for j, lap in enumerate(splits, 1):
                    lap_distance_mi = lap.get('distance', 0) / 1609.34
                    lap_duration = lap.get('duration', 0)
                    lap_avg_speed = lap.get('averageSpeed', 0)
                    lap_avg_hr = lap.get('averageHR')
                    lap_max_hr = lap.get('maxHR')

                    hr_avg_str = f"{int(lap_avg_hr)}" if lap_avg_hr else "-"
                    hr_max_str = f"{int(lap_max_hr)}" if lap_max_hr else "-"

                    f.write(f"| {j} | {lap_distance_mi:.2f} mi | {format_duration(lap_duration)} | ")
                    f.write(f"{format_pace(lap_avg_speed)} | {hr_avg_str} | {hr_max_str} |\n")

                f.write("\n")

            # Notes/description
            description = activity.get('description', '').strip()
            if description:
                f.write("### Notes\n\n")
                f.write(f"{description}\n\n")

            f.write("---\n\n")

        # Add coaching analysis prompt
        f.write("\n## Analysis Request\n\n")
        f.write("Please analyze my recent training and provide insights on:\n\n")
        f.write("1. **Training consistency:** Am I following a consistent pattern?\n")
        f.write("2. **Pace distribution:** Are my easy runs easy enough? Are quality sessions hitting targets?\n")
        f.write("3. **Recovery indicators:** Do HR and pace metrics suggest adequate recovery?\n")
        f.write("4. **Workout execution:** For structured workouts, how consistent are my splits?\n")
        f.write("5. **Areas of concern:** Any red flags or patterns to address?\n")
        f.write("6. **Recommendations:** What adjustments would improve my training?\n\n")
        f.write("Context: Training for NYC Marathon 2026 with a 3:05 goal (7:02/mile pace). ")
        f.write("Current PR is 3:19. Following Pfitzinger 18/55 plan.\n")


def main():
    parser = argparse.ArgumentParser(
        description='Export Garmin activities for training analysis'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=15,
        help='Number of days to look back (default: 15)'
    )

    parser.add_argument(
        '--output',
        default='training_log.md',
        help='Output filename (default: training_log.md)'
    )

    args = parser.parse_args()

    print("Authenticating with Garmin Connect...")
    api = authenticate()
    print("✓ Authenticated\n")

    activities = get_recent_activities(api, days=args.days)

    if not activities:
        print("No activities found in the specified time period")
        return

    print(f"Found {len(activities)} activities\n")

    export_to_markdown(api, activities, args.output)

    print(f"\n✓ Export complete: {args.output}")
    print("\nNext steps:")
    print(f"1. Review the file: {args.output}")
    print("2. Share it with Claude for personalized training analysis")


if __name__ == '__main__':
    main()
