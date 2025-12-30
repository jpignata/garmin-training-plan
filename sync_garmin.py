#!/usr/bin/env python3
"""
Garmin Training Plan Sync Script

Syncs training plans from YAML to Garmin Connect with support for:
- upload-all: Upload entire training plan
- delete-all: Delete all scheduled workouts
- update-week: Update specific week
"""

import argparse
import os
import sys
import yaml
import logging
from datetime import datetime, timedelta
from pathlib import Path
from garminconnect import Garmin
from dateutil.parser import parse as parse_date
from garmin_workout_builder import WorkoutBuilder
import garth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GarminTrainingPlanSync:
    """Manages syncing training plans to Garmin Connect"""

    def __init__(self, plan_file: str):
        self.plan_file = Path(plan_file)
        self.plan_data = None
        self.api = None
        self.workout_builder = None

    def delete_workout(self, workout_id: int) -> bool:
        """
        Delete a workout from the library.

        Args:
            workout_id: The Garmin workout ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Construct the delete endpoint
            url = f"/workout-service/workout/{workout_id}"

            logger.debug(f"      Deleting workout {workout_id}")

            # DELETE request to remove the workout
            result = self.api.garth.request("DELETE", "connectapi", url, api=True)

            if result.status_code in [200, 204]:
                logger.debug(f"      ✓ Deleted successfully")
                return True
            else:
                logger.warning(f"      Delete returned status {result.status_code}")
                return False

        except Exception as e:
            logger.error(f"      ✗ Failed to delete: {e}")
            return False

    def schedule_workout(self, workout_id: int, date: datetime) -> bool:
        """
        Schedule a workout to a specific date on the calendar.

        Args:
            workout_id: The Garmin workout ID
            date: The date to schedule the workout

        Returns:
            True if successful, False otherwise
        """
        try:
            # Format date as YYYY-MM-DD
            date_str = date.strftime('%Y-%m-%d')

            # Construct the scheduling endpoint
            url = f"/workout-service/schedule/{workout_id}"

            # Payload with the date
            payload = {
                "date": date_str
            }

            logger.debug(f"      Scheduling workout {workout_id} to {date_str}")

            # POST to the schedule endpoint
            result = self.api.garth.post("connectapi", url, json=payload, api=True)

            if result.status_code in [200, 201, 204]:
                logger.debug(f"      ✓ Scheduled successfully")
                return True
            else:
                logger.warning(f"      Schedule returned status {result.status_code}")
                return False

        except Exception as e:
            logger.error(f"      ✗ Failed to schedule: {e}")
            return False

    def authenticate(self):
        """Authenticate with Garmin Connect using environment variables"""
        email = os.getenv('GARMIN_EMAIL')
        password = os.getenv('GARMIN_PASSWORD')

        if not email or not password:
            logger.error("GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set")
            sys.exit(1)

        tokenstore_dir = os.path.expanduser("~/.garminconnect")

        try:
            # Login with credentials using garth directly
            logger.info("Authenticating with Garmin Connect...")

            # Try to use existing tokens first
            if os.path.exists(tokenstore_dir):
                logger.info("Attempting to use saved authentication tokens...")
                try:
                    garth.resume(tokenstore_dir)

                    # Create Garmin API instance with the resumed garth client
                    self.api = Garmin()
                    self.api.garth = garth.client
                    self.api.username = email

                    # Verify tokens work
                    full_name = self.api.get_full_name()
                    logger.info(f"Successfully authenticated as {full_name}")
                    return  # Success, we're done

                except Exception:
                    logger.warning("Failed to use cached tokens, logging in again...")
                    # Remove invalid tokens and login fresh
                    import shutil
                    shutil.rmtree(tokenstore_dir, ignore_errors=True)

                    # Login with MFA prompt callback
                    garth.login(email, password, prompt_mfa=lambda: input("Enter MFA code: ").strip())
                    garth.save(tokenstore_dir)
                    logger.info(f"Authentication tokens saved to: {tokenstore_dir}")
            else:
                # Fresh login with MFA support
                garth.login(email, password, prompt_mfa=lambda: input("Enter MFA code: ").strip())
                garth.save(tokenstore_dir)
                logger.info(f"Authentication tokens saved to: {tokenstore_dir}")

            # Create Garmin API instance and connect it to our authenticated garth client
            self.api = Garmin()
            # Replace the Garmin instance's garth client with our authenticated one
            self.api.garth = garth.client
            self.api.username = email

            # Verify authentication
            try:
                full_name = self.api.get_full_name()
                logger.info(f"Successfully authenticated as {full_name}")
            except Exception as e:
                logger.info("Successfully authenticated with Garmin Connect")

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "too many" in error_msg:
                logger.error("Too many login attempts. Please wait 30 minutes and try again.")
            elif "401" in error_msg or "403" in error_msg or "invalid" in error_msg:
                logger.error("Invalid credentials or MFA code. Please check your email/password.")
            else:
                logger.error(f"Login failed: {e}")
                logger.error("\nTroubleshooting tips:")
                logger.error("1. Verify your GARMIN_EMAIL and GARMIN_PASSWORD are correct")
                logger.error("2. Try clearing cached tokens: rm -rf ~/.garminconnect")
                logger.error("3. Make sure you can log in to https://connect.garmin.com with these credentials")
            sys.exit(1)

    def load_plan(self):
        """Load and validate training plan from YAML"""
        if not self.plan_file.exists():
            logger.error(f"Plan file not found: {self.plan_file}")
            sys.exit(1)

        try:
            with open(self.plan_file, 'r') as f:
                self.plan_data = yaml.safe_load(f)

            # Validate required fields
            required_fields = ['goal_event', 'plan', 'paces', 'weeks']
            for field in required_fields:
                if field not in self.plan_data:
                    raise ValueError(f"Missing required field: {field}")

            logger.info(f"Loaded plan: {self.plan_data['plan']['name']}")
            logger.info(f"Goal event: {self.plan_data['goal_event']['name']} on {self.plan_data['goal_event']['date']}")
            logger.info(f"Weeks: {len(self.plan_data['weeks'])}")

            # Initialize workout builder with paces
            self.workout_builder = WorkoutBuilder(self.plan_data['paces'])

        except Exception as e:
            logger.error(f"Failed to load plan: {e}")
            sys.exit(1)

    def calculate_week_start_date(self, week_number: int) -> datetime:
        """
        Calculate the start date (Monday) for a given week number.
        Works backwards from race date.
        """
        race_date_str = self.plan_data['goal_event']['date']
        race_date = parse_date(race_date_str)

        # Race date is a Sunday (the end of week 19)
        # Work backwards: week N's Sunday = race_date - (19 - N) weeks
        weeks_before_race = 19 - week_number
        week_sunday = race_date - timedelta(weeks=weeks_before_race)

        # Week starts on Monday, which is 6 days before Sunday
        week_monday = week_sunday - timedelta(days=6)

        return week_monday

    def get_workout_date(self, week_number: int, day_name: str) -> datetime:
        """Get the specific date for a workout given week and day name"""
        week_start = self.calculate_week_start_date(week_number)

        # Week starts on Monday
        day_offset = {
            'monday': 0,
            'tuesday': 1,
            'wednesday': 2,
            'thursday': 3,
            'friday': 4,
            'saturday': 5,
            'sunday': 6
        }

        offset = day_offset.get(day_name.lower())
        if offset is None:
            raise ValueError(f"Invalid day name: {day_name}")

        return week_start + timedelta(days=offset)

    def upload_all(self):
        """Upload entire training plan to Garmin Connect"""
        logger.info("Starting upload of entire training plan...")

        total_workouts = 0
        uploaded_workouts = 0
        skipped_workouts = 0

        for week in self.plan_data['weeks']:
            week_number = week['week']
            logger.info(f"\nProcessing Week {week_number} ({week['block']})...")

            for day_name, workout in week['workouts'].items():
                workout_date = self.get_workout_date(week_number, day_name)

                # Skip rest days
                if workout.get('type') == 'rest':
                    logger.debug(f"  {day_name.capitalize()}: Rest day (skipped)")
                    skipped_workouts += 1
                    continue

                total_workouts += 1

                try:
                    logger.info(f"  {day_name.capitalize()} ({workout_date.strftime('%Y-%m-%d')}): {workout.get('type')} - {workout.get('description', 'N/A')[:50]}")

                    # Convert workout to Garmin format
                    logger.debug(f"    Converting workout to Garmin format...")
                    workout_json = self.workout_builder.build_workout_from_yaml(
                        workout, workout_date, week_number, day_name
                    )

                    logger.debug(f"    Workout: {workout_json.get('workoutName', 'N/A')}")
                    logger.debug(f"    Steps: {len(workout_json.get('workoutSegments', [{}])[0].get('workoutSteps', []))}")

                    # Upload workout to Garmin Connect
                    logger.debug(f"    Uploading to Garmin Connect...")
                    result = self.api.upload_workout(workout_json)

                    if result:
                        workout_id = result.get('workoutId')
                        logger.info(f"    ✓ Uploaded successfully: workout_id={workout_id}")

                        # Schedule workout to specific date
                        if workout_id:
                            if self.schedule_workout(workout_id, workout_date):
                                logger.info(f"    ✓ Scheduled to calendar: {workout_date.strftime('%Y-%m-%d')}")
                            else:
                                logger.warning(f"    Upload succeeded but scheduling failed")

                        uploaded_workouts += 1
                    else:
                        logger.warning(f"    Upload returned no result")

                except Exception as e:
                    logger.error(f"  ✗ Failed to upload {day_name}: {e}")
                    import traceback
                    logger.debug(f"    Traceback:\n{traceback.format_exc()}")

        logger.info(f"\nUpload complete!")
        logger.info(f"Total workouts: {total_workouts}")
        logger.info(f"Uploaded: {uploaded_workouts}")
        logger.info(f"Skipped (rest days): {skipped_workouts}")

    def delete_all(self):
        """Delete all workouts from the plan"""
        logger.info("Starting deletion of all workouts from the plan...")

        try:
            # Get all workouts
            logger.info("Fetching workouts from Garmin Connect...")
            workouts_data = self.api.get_workouts(start=0, limit=1000)

            if not workouts_data:
                logger.warning("No workouts found")
                return

            workouts = workouts_data if isinstance(workouts_data, list) else [workouts_data]

            # Filter workouts that match our plan name pattern
            plan_workouts = []
            for workout in workouts:
                workout_name = workout.get('workoutName', '')
                if 'NYC Marathon 2026' in workout_name:
                    plan_workouts.append(workout)

            logger.info(f"Found {len(plan_workouts)} workouts for NYC Marathon 2026 plan")

            if not plan_workouts:
                logger.info("No workouts to delete")
                return

            # Delete each workout
            deleted_count = 0
            failed_count = 0

            for workout in plan_workouts:
                workout_id = workout.get('workoutId')
                workout_name = workout.get('workoutName', 'Unknown')

                try:
                    logger.info(f"  Deleting: {workout_name} (ID: {workout_id})")

                    if self.delete_workout(workout_id):
                        logger.info(f"    ✓ Deleted successfully")
                        deleted_count += 1
                    else:
                        logger.warning(f"    ✗ Deletion failed")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"  ✗ Failed to delete {workout_name}: {e}")
                    failed_count += 1

            logger.info(f"\nDeletion summary:")
            logger.info(f"  Total found: {len(plan_workouts)}")
            logger.info(f"  Deleted: {deleted_count}")
            logger.info(f"  Failed: {failed_count}")

        except Exception as e:
            logger.error(f"Failed to delete workouts: {e}")

    def update_week(self, week_number: int):
        """Update a specific week by deleting old workouts and re-uploading"""
        logger.info(f"Updating week {week_number}...")

        # Validate week number
        week_numbers = [w['week'] for w in self.plan_data['weeks']]
        if week_number not in week_numbers:
            logger.error(f"Invalid week number: {week_number}. Available weeks: {week_numbers}")
            return

        # Find the week data
        week_data = None
        for week in self.plan_data['weeks']:
            if week['week'] == week_number:
                week_data = week
                break

        if not week_data:
            logger.error(f"Week {week_number} not found in plan")
            return

        # Calculate week date range
        week_start = self.calculate_week_start_date(week_number)
        week_end = week_start + timedelta(days=6)

        logger.info(f"Week {week_number} date range: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}")

        # Step 1: Delete existing workouts for this week
        logger.info("\nStep 1: Deleting existing workouts for this week...")
        try:
            workouts_data = self.api.get_workouts(start=0, limit=1000)
            workouts = workouts_data if isinstance(workouts_data, list) else [workouts_data]

            deleted_count = 0
            for workout in workouts:
                workout_name = workout.get('workoutName', '')
                if f'Week {week_number}' in workout_name and 'NYC Marathon 2026' in workout_name:
                    workout_id = workout.get('workoutId')
                    logger.info(f"  Deleting: {workout_name} (ID: {workout_id})")

                    if self.delete_workout(workout_id):
                        logger.info(f"    ✓ Deleted successfully")
                        deleted_count += 1
                    else:
                        logger.warning(f"    ✗ Deletion failed")

            logger.info(f"Deleted {deleted_count} workouts")

        except Exception as e:
            logger.error(f"Failed to delete workouts: {e}")

        # Step 2: Upload new workouts for this week
        logger.info("\nStep 2: Uploading new workouts for this week...")

        uploaded_count = 0
        failed_count = 0

        for day_name, workout in week_data['workouts'].items():
            workout_date = self.get_workout_date(week_number, day_name)

            # Skip rest days
            if workout.get('type') == 'rest':
                logger.debug(f"  {day_name.capitalize()}: Rest day (skipped)")
                continue

            try:
                logger.info(f"  {day_name.capitalize()} ({workout_date.strftime('%Y-%m-%d')}): {workout.get('type')}")

                # Convert workout to Garmin format
                logger.debug(f"    Converting workout to Garmin format...")
                workout_json = self.workout_builder.build_workout_from_yaml(
                    workout, workout_date, week_number, day_name
                )

                logger.debug(f"    Workout: {workout_json.get('workoutName', 'N/A')}")
                logger.debug(f"    Steps: {len(workout_json.get('workoutSegments', [{}])[0].get('workoutSteps', []))}")

                # Upload workout
                logger.debug(f"    Uploading to Garmin Connect...")
                result = self.api.upload_workout(workout_json)

                if result:
                    workout_id = result.get('workoutId')
                    logger.info(f"    ✓ Uploaded successfully: workout_id={workout_id}")

                    # Schedule workout to specific date
                    if workout_id:
                        if self.schedule_workout(workout_id, workout_date):
                            logger.info(f"    ✓ Scheduled to calendar: {workout_date.strftime('%Y-%m-%d')}")
                        else:
                            logger.warning(f"    Upload succeeded but scheduling failed")

                    uploaded_count += 1
                else:
                    logger.warning(f"    Upload returned no result")
                    failed_count += 1

            except Exception as e:
                logger.error(f"  ✗ Failed to upload {day_name}: {e}")
                import traceback
                logger.debug(f"    Traceback:\n{traceback.format_exc()}")
                failed_count += 1

        logger.info(f"\nUpdate complete!")
        logger.info(f"Uploaded: {uploaded_count}")
        logger.info(f"Failed: {failed_count}")


def main():
    parser = argparse.ArgumentParser(
        description='Sync training plans from YAML to Garmin Connect',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s upload-all                    Upload entire training plan
  %(prog)s delete-all                    Delete all scheduled workouts
  %(prog)s update-week 5                 Update week 5 of the plan

Environment Variables:
  GARMIN_EMAIL      Your Garmin Connect email
  GARMIN_PASSWORD   Your Garmin Connect password
        """
    )

    parser.add_argument(
        'command',
        choices=['upload-all', 'delete-all', 'update-week'],
        help='Operation to perform'
    )

    parser.add_argument(
        'week',
        type=int,
        nargs='?',
        help='Week number (required for update-week command)'
    )

    parser.add_argument(
        '--plan',
        default='plans/nyc_marathon_2026.yaml',
        help='Path to training plan YAML file (default: plans/nyc_marathon_2026.yaml)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate arguments
    if args.command == 'update-week' and args.week is None:
        parser.error("update-week requires a week number")

    # Create syncer and authenticate
    syncer = GarminTrainingPlanSync(args.plan)
    syncer.authenticate()
    syncer.load_plan()

    # Execute command
    if args.command == 'upload-all':
        syncer.upload_all()
    elif args.command == 'delete-all':
        syncer.delete_all()
    elif args.command == 'update-week':
        syncer.update_week(args.week)


if __name__ == '__main__':
    main()
