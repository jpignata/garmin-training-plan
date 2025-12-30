# Garmin Training Plan Sync

A Python CLI tool to sync marathon training plans from YAML format to Garmin Connect.

> ✨ Vibe coded with [Claude Code](https://claude.com/claude-code)

## Features

- **Upload Training Plans**: Create structured workouts with pace zones, intervals, warmup/cooldown
- **Delete Workouts**: Remove all workouts from a plan
- **Update Specific Weeks**: Re-upload a specific week of training
- **Structured Workouts**: Full detail with pace targets, interval steps, and proper structure

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

Set your Garmin Connect credentials as environment variables:

```bash
export GARMIN_EMAIL="your@email.com"
export GARMIN_PASSWORD="your_password"
```

### MFA/2FA Support

If you have multi-factor authentication enabled on your Garmin account, the script will prompt for your MFA code during the first login. After successful authentication, tokens are saved to `~/.garminconnect` and are valid for approximately one year, so you won't need to enter MFA codes on subsequent runs.

## Usage

### Upload Entire Plan

Upload all 19 weeks of the training plan (18 training weeks + race week):

```bash
python sync_garmin.py upload-all
```

### Delete All Workouts

Delete all workouts associated with the plan:

```bash
python sync_garmin.py delete-all
```

### Update Specific Week

Update a specific week (e.g., week 5):

```bash
python sync_garmin.py update-week 5
```

### Options

- `--plan PATH`: Path to training plan YAML file (default: `plans/nyc_marathon_2026.yaml`)
- `--verbose, -v`: Enable verbose logging

## Training Plan Format

The training plan is stored in YAML format with the following structure:

```yaml
goal_event:
  name: NYC Marathon 2026
  date: '2026-11-01'
  type: marathon
  distance: 26.2
  goal_time: '3:05:00'

plan:
  name: Pfitzinger 18/55
  duration_weeks: 18
  peak_mileage: 55
  # Note: 18 training weeks + week 19 (race week) = 19 total weeks

paces:
  recovery: '9:15'
  general_aerobic: '8:30'
  marathon_pace: '7:02'
  lactate_threshold: '6:40'
  vo2max: '6:08'

weeks:
  - week: 1
    block: Endurance
    workouts:
      monday:
        type: rest
      tuesday:
        type: lactate_threshold
        distance: 8-9
        description: 'LT run: 8-9 miles with 20-25 minutes at LT pace'
        structure:
          warmup:
            distance: 2
            pace: general_aerobic
          main:
            duration: 20-25 min
            pace: lactate_threshold
          cooldown:
            distance: 2
            pace: general_aerobic
      # ... more days
  - week: 2
    # ... more weeks
  # ... up to week 19 (race week)
```

## Workout Conversion

### Distance Ranges
- Uses maximum value (e.g., "8-9 miles" → 9 miles)

### Rest Days
- Skipped (no workout created)

### Structured Workouts
Converts YAML workout structure to Garmin format with:
- **Warmup**: Distance-based warmup at aerobic pace
- **Intervals**: Repeat groups with work/rest segments
- **Main Work**: LT or marathon pace segments
- **Cooldown**: Distance-based cooldown

### Pace Targets
- Converts pace (min:sec per mile) to speed (meters per second)
- Creates pace targets with ±5% range for flexibility
- Uses `targetTypeId: 6` with `targetTypeKey: "pace.zone"`
- Target values (targetValueOne/targetValueTwo) are specified in meters per second at the step level

## Current Status

### ✅ Fully Implemented
- CLI interface with argument parsing
- Authentication with Garmin Connect (with MFA support)
- YAML parsing and validation
- Date calculation (week numbers → calendar dates)
- Workout builder with structured workouts
- Pace zone mapping to speed targets with ±5% range
- Upload-all operation (creates and schedules workouts)
- Delete-all operation (removes all workouts from plan)
- Update-week operation (re-uploads specific week)
- **Workout Scheduling**: Workouts automatically scheduled to calendar dates
- **Pace Targets**: Properly configured to display as pace zones (not heart rate)

## Technical Details

### Garmin Workout Structure

Workouts use the following JSON structure:

```json
{
  "workoutName": "NYC Marathon 2026 - Week 5 - Tuesday",
  "description": "LT run: 8-9 miles with 20-25 minutes at LT pace",
  "sportType": {
    "sportTypeId": 1,
    "sportTypeKey": "running"
  },
  "estimatedDurationInSecs": 3600,
  "workoutSegments": [
    {
      "segmentOrder": 1,
      "sportType": {...},
      "workoutSteps": [
        {
          "type": "ExecutableStepDTO",
          "stepOrder": 1,
          "stepType": {
            "stepTypeId": 1,
            "stepTypeKey": "warmup"
          },
          "endCondition": {
            "conditionTypeId": 3,
            "conditionTypeKey": "distance"
          },
          "endConditionValue": 3218.68,
          "targetType": {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone"
          },
          "targetValueOne": 3.8,
          "targetValueTwo": 4.2
        }
        // ... more steps
      ]
    }
  ]
}
```

### Step Types
- 1: Warmup
- 2: Cooldown
- 3: Interval (main work)
- 4: Recovery
- 5: Rest
- 6: Repeat Group

### End Conditions
- 1: Lap Button
- 2: Time (seconds)
- 3: Distance (meters)

### Target Types
- 1: No Target
- 2: Heart Rate Zone
- 3: Cadence
- 4: Heart Rate (custom)
- 5: Speed (km/h)
- 6: Pace Zone (min/km or min/mile)
- 7: Power

## Research Resources

Based on web research and reverse engineering:
- [GitHub: ThomasRondof/GarminWorkoutAItoJSON](https://github.com/ThomasRondof/GarminWorkoutAItoJSON) - Used to discover pace target format
- [GitHub: mkuthan/garmin-workouts](https://github.com/mkuthan/garmin-workouts) - Command line tool for managing Garmin workouts
- [GitHub: cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect) - Python API wrapper
- [Garmin Connect Training API](https://developer.garmin.com/gc-developer-program/training-api/)

### Key Discoveries

**Pace Targets**: The correct format for pace targets is `targetTypeId: 6` with `targetTypeKey: "pace.zone"`. Using `targetTypeId: 4` results in Garmin interpreting values as heart rate (BPM) instead of pace.

**Workout Scheduling**: POST to `/workout-service/schedule/{workout_id}` with `{"date": "YYYY-MM-DD"}`

**Workout Deletion**: DELETE to `/workout-service/workout/{workout_id}`

## License

MIT License
