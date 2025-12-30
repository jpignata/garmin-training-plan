# Garmin Training Plan Sync

A Python CLI tool to sync marathon training plans from YAML format to Garmin Connect.

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

Upload all 18 weeks of the training plan:

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

paces:
  recovery: '9:15'
  general_aerobic: '8:30'
  marathon_pace: '7:02'
  lactate_threshold: '6:40'
  vo2max: '6:08'

weeks:
  - week: 18
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
- Creates speed targets with ±5% range for flexibility

## Current Status

### ✅ Implemented
- CLI interface with argument parsing
- Authentication with Garmin Connect (with MFA support)
- YAML parsing and validation
- Date calculation (week numbers → calendar dates)
- Workout builder with structured workouts
- Pace zone mapping to speed targets
- Upload-all operation (creates and schedules workouts)
- Update-week operation (re-uploads and schedules specific week)
- **Workout Scheduling**: Workouts are now automatically scheduled to calendar dates!

### ⚠️ In Progress
- **Workout Deletion**: Can identify workouts to delete but API endpoint not yet implemented

### 🔧 To Do
1. **Implement Workout Deletion**
   - Find the correct API endpoint for deleting workouts from library
   - May need to use garminconnect internal request methods
   - Test deletion and re-uploading flow

2. **Add Pace Target Values**
   - Include `targetValueOne` and `targetValueTwo` in workout steps
   - Test if Garmin Connect properly displays pace targets

3. **Testing**
   - Verify workout structure appears correctly in Garmin Connect
   - Verify workouts appear on calendar with correct dates
   - Test pace targets display correctly on Garmin devices

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
            "workoutTargetTypeId": 4,
            "workoutTargetTypeKey": "speed"
          }
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
- 2: Heart Rate
- 3: Cadence
- 4: Speed
- 5: Power
- 6: Open

## Research Resources

Based on web research:
- [GitHub: sydspost/Garmin-Connect-Workout-and-Schedule-creator](https://github.com/sydspost/Garmin-Connect-Workout-and-Schedule-creator)
- [Garmin Connect Training API](https://developer.garmin.com/gc-developer-program/training-api/)
- [GitHub: cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect)

The recommended approach for understanding Garmin's workout JSON structure is to:
1. Create a workout manually in Garmin Connect
2. Export it to JSON format
3. Examine the structure for scheduling and target fields

## Contributing

To implement the missing features:

1. **Scheduling API**: Look for POST endpoints at `{garmin_workouts_schedule_url}` or similar
2. **Deletion API**: Look for DELETE endpoints for workout library items
3. **Target Values**: Add `targetValueOne`, `targetValueTwo`, or `zoneNumber` fields to workout steps

## License

MIT License
