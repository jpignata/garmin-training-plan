"""
Garmin Workout Builder

Converts training plan workouts from YAML format to Garmin Connect API format.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class WorkoutBuilder:
    """Builds Garmin Connect workout JSON from training plan data"""

    def __init__(self, paces: Dict[str, str]):
        """
        Initialize workout builder with pace zones.

        Args:
            paces: Dictionary mapping pace zone names to pace values (e.g., {'marathon_pace': '7:02'})
        """
        self.paces = paces

    def parse_distance(self, distance_str: str | int | float) -> float:
        """
        Parse distance from string or number, using maximum value for ranges.

        Args:
            distance_str: Distance as string (e.g., "8-9", "10") or number

        Returns:
            Distance in miles as float
        """
        if isinstance(distance_str, (int, float)):
            return float(distance_str)

        distance_str = str(distance_str).strip()

        # Handle ranges like "8-9" - use maximum per user preference
        if '-' in distance_str:
            parts = distance_str.split('-')
            return float(parts[1].strip())

        return float(distance_str)

    def parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string to seconds.

        Args:
            duration_str: Duration string (e.g., "20-25 min", "30 sec", "1:30:00")

        Returns:
            Duration in seconds
        """
        duration_str = duration_str.strip().lower()

        # Handle ranges like "20-25 min" - use maximum per user preference
        if '-' in duration_str:
            parts = duration_str.split('-')
            duration_str = parts[1].strip()

        # Parse "XX min" format
        if 'min' in duration_str:
            minutes = float(duration_str.replace('min', '').strip())
            return int(minutes * 60)

        # Parse "XX sec" format
        if 'sec' in duration_str:
            return int(float(duration_str.replace('sec', '').strip()))

        # Parse "HH:MM:SS" or "MM:SS" format
        if ':' in duration_str:
            parts = duration_str.split(':')
            if len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])

        # Default: assume it's a number of seconds
        return int(float(duration_str))

    def pace_to_speed(self, pace_str: str) -> float:
        """
        Convert pace (min:sec per mile) to speed (meters per second).

        Args:
            pace_str: Pace string (e.g., "7:02" for 7:02 per mile)

        Returns:
            Speed in meters per second
        """
        parts = pace_str.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])

        pace_seconds_per_mile = minutes * 60 + seconds

        # Convert to meters per second
        meters_per_mile = 1609.34
        speed_mps = meters_per_mile / pace_seconds_per_mile

        return speed_mps

    def get_target_speed_zone(self, pace_zone: str) -> Dict[str, Any]:
        """
        Get speed target zone for a given pace name.

        Args:
            pace_zone: Name of pace zone (e.g., 'marathon_pace', 'recovery')

        Returns:
            Target type dictionary with speed zone
        """
        if pace_zone not in self.paces:
            logger.warning(f"Unknown pace zone: {pace_zone}, using no target")
            return self.get_no_target()

        pace_str = self.paces[pace_zone]
        speed_mps = self.pace_to_speed(pace_str)

        # Create speed target with ±5% range
        target_low = speed_mps * 0.95
        target_high = speed_mps * 1.05

        # Use targetTypeId 6 for pace targets (not 4 which is heart rate!)
        return {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "targetValueOne": target_low,
            "targetValueTwo": target_high
        }

    def get_no_target(self) -> Dict[str, Any]:
        """Get 'no target' type"""
        return {
            "workoutTargetTypeId": 1,
            "workoutTargetTypeKey": "no.target"
        }

    def create_executable_step(
        self,
        step_order: int,
        step_type_id: int,
        step_type_key: str,
        end_condition_id: int,
        end_condition_key: str,
        end_condition_value: float,
        target_type: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an executable workout step.

        Args:
            step_order: Order of step in workout
            step_type_id: Step type ID (1=warmup, 2=cooldown, 3=interval, 4=recovery)
            step_type_key: Step type key string
            end_condition_id: End condition type ID (1=lap.button, 2=time, 3=distance, etc.)
            end_condition_key: End condition key string
            end_condition_value: Value for end condition (seconds for time, meters for distance)
            target_type: Optional target type dictionary

        Returns:
            ExecutableStepDTO dictionary
        """
        target = target_type or self.get_no_target()

        # Extract target values if they exist
        target_value_one = target.pop('targetValueOne', None)
        target_value_two = target.pop('targetValueTwo', None)

        step = {
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": {
                "stepTypeId": step_type_id,
                "stepTypeKey": step_type_key
            },
            "endCondition": {
                "conditionTypeId": end_condition_id,
                "conditionTypeKey": end_condition_key
            },
            "endConditionValue": end_condition_value,
            "targetType": target
        }

        # Add target values at step level, not nested in targetType
        if target_value_one is not None:
            step["targetValueOne"] = target_value_one
        if target_value_two is not None:
            step["targetValueTwo"] = target_value_two

        return step

    def create_repeat_group(
        self,
        step_order: int,
        iterations: int,
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a repeat group for interval workouts.

        Args:
            step_order: Order of repeat group in workout
            iterations: Number of times to repeat
            steps: List of executable steps to repeat

        Returns:
            RepeatGroupDTO dictionary
        """
        return {
            "type": "RepeatGroupDTO",
            "stepOrder": step_order,
            "numberOfIterations": iterations,
            "workoutSteps": steps
        }

    def build_workout_from_yaml(
        self,
        workout_data: Dict[str, Any],
        workout_date: datetime,
        week_number: int,
        day_name: str
    ) -> Dict[str, Any]:
        """
        Build a complete Garmin workout from YAML workout data.

        Args:
            workout_data: Workout dictionary from YAML
            workout_date: Date to schedule workout
            week_number: Week number in plan
            day_name: Day name (monday, tuesday, etc.)

        Returns:
            Complete workout JSON for Garmin Connect API
        """
        workout_type = workout_data.get('type', 'general_aerobic')
        description = workout_data.get('description', '')
        distance = workout_data.get('distance')

        # Create workout name
        workout_name = f"NYC Marathon 2026 - Week {week_number} - {day_name.capitalize()}"

        # Build workout steps
        steps = []
        step_order = 1

        # Check if workout has structured steps
        if 'structure' in workout_data:
            steps = self._build_structured_workout(workout_data['structure'], step_order)
        else:
            # Build simple workout based on type and distance
            steps = self._build_simple_workout(workout_type, distance, step_order)

        # Calculate estimated duration (rough estimate)
        estimated_duration = self._estimate_duration(workout_data)

        # Build complete workout JSON
        workout_json = {
            "workoutName": workout_name,
            "description": description,
            "sportType": {
                "sportTypeId": 1,  # Running
                "sportTypeKey": "running"
            },
            "estimatedDurationInSecs": estimated_duration,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {
                        "sportTypeId": 1,
                        "sportTypeKey": "running",
                        "displayOrder": 1
                    },
                    "workoutSteps": steps
                }
            ]
        }

        return workout_json

    def _build_structured_workout(
        self,
        structure: Dict[str, Any],
        start_order: int
    ) -> List[Dict[str, Any]]:
        """Build structured workout with warmup, main, intervals, cooldown"""
        steps = []
        step_order = start_order

        # Warmup
        if 'warmup' in structure:
            warmup = structure['warmup']
            distance_miles = self.parse_distance(warmup.get('distance', 2))
            distance_meters = distance_miles * 1609.34
            pace_zone = warmup.get('pace', 'general_aerobic')

            steps.append(self.create_executable_step(
                step_order=step_order,
                step_type_id=1,  # WARMUP
                step_type_key="warmup",
                end_condition_id=3,  # DISTANCE
                end_condition_key="distance",
                end_condition_value=distance_meters,
                target_type=self.get_target_speed_zone(pace_zone)
            ))
            step_order += 1

        # Intervals
        if 'intervals' in structure:
            intervals = structure['intervals']
            repeat_steps = []

            # Work interval
            work = intervals.get('work', {})

            # Check if work interval is time-based or distance-based
            if 'duration' in work:
                # Time-based work interval (e.g., LT intervals)
                duration_str = work['duration']
                duration_secs = self.parse_duration(duration_str)

                repeat_steps.append(self.create_executable_step(
                    step_order=1,
                    step_type_id=3,  # INTERVAL
                    step_type_key="interval",
                    end_condition_id=2,  # TIME
                    end_condition_key="time",
                    end_condition_value=duration_secs,
                    target_type=self.get_target_speed_zone(work.get('pace', 'lactate_threshold'))
                ))
            else:
                # Distance-based work interval (e.g., VO2max intervals)
                work_distance_meters = work.get('distance', 600)
                if work.get('unit') == 'meters':
                    work_distance_meters = work_distance_meters
                else:
                    work_distance_meters = work_distance_meters * 1609.34

                repeat_steps.append(self.create_executable_step(
                    step_order=1,
                    step_type_id=3,  # INTERVAL
                    step_type_key="interval",
                    end_condition_id=3,  # DISTANCE
                    end_condition_key="distance",
                    end_condition_value=work_distance_meters,
                    target_type=self.get_target_speed_zone(work.get('pace', 'vo2max'))
                ))

            # Rest interval
            rest = intervals.get('rest', {})
            if rest.get('type') == 'jog':
                # Parse rest duration if provided, otherwise use default
                if 'duration' in rest:
                    rest_duration = self.parse_duration(rest['duration'])
                else:
                    rest_duration = 150  # default 2.5 minutes

                repeat_steps.append(self.create_executable_step(
                    step_order=2,
                    step_type_id=4,  # RECOVERY
                    step_type_key="recovery",
                    end_condition_id=2,  # TIME
                    end_condition_key="time",
                    end_condition_value=rest_duration,
                    target_type=self.get_no_target()  # No pace target for recovery jogs
                ))

            # Create repeat group
            iterations = intervals.get('repeat', 1)
            steps.append(self.create_repeat_group(
                step_order=step_order,
                iterations=iterations,
                steps=repeat_steps
            ))
            step_order += 1

        # Main work (for non-interval workouts)
        if 'main' in structure and 'intervals' not in structure:
            main = structure['main']

            if 'duration' in main:
                duration_str = main['duration']
                duration_secs = self.parse_duration(duration_str)

                steps.append(self.create_executable_step(
                    step_order=step_order,
                    step_type_id=3,  # INTERVAL (main work)
                    step_type_key="interval",
                    end_condition_id=2,  # TIME
                    end_condition_key="time",
                    end_condition_value=duration_secs,
                    target_type=self.get_target_speed_zone(main.get('pace', 'lactate_threshold'))
                ))
            elif 'distance' in main:
                distance_miles = self.parse_distance(main['distance'])
                distance_meters = distance_miles * 1609.34

                steps.append(self.create_executable_step(
                    step_order=step_order,
                    step_type_id=3,  # INTERVAL
                    step_type_key="interval",
                    end_condition_id=3,  # DISTANCE
                    end_condition_key="distance",
                    end_condition_value=distance_meters,
                    target_type=self.get_target_speed_zone(main.get('pace', 'marathon_pace'))
                ))

            step_order += 1

        # Cooldown
        if 'cooldown' in structure:
            cooldown = structure['cooldown']
            distance_miles = self.parse_distance(cooldown.get('distance', 2))
            distance_meters = distance_miles * 1609.34
            pace_zone = cooldown.get('pace', 'general_aerobic')

            steps.append(self.create_executable_step(
                step_order=step_order,
                step_type_id=2,  # COOLDOWN
                step_type_key="cooldown",
                end_condition_id=3,  # DISTANCE
                end_condition_key="distance",
                end_condition_value=distance_meters,
                target_type=self.get_target_speed_zone(pace_zone)
            ))

        return steps

    def _build_simple_workout(
        self,
        workout_type: str,
        distance: Optional[float],
        start_order: int
    ) -> List[Dict[str, Any]]:
        """Build a simple single-step workout"""
        if not distance:
            distance = 5  # Default distance

        distance_miles = self.parse_distance(distance)
        distance_meters = distance_miles * 1609.34

        # Map workout type to pace zone
        pace_zone_map = {
            'recovery': 'recovery',
            'general_aerobic': 'general_aerobic',
            'endurance': 'endurance',
            'medium_long_run': 'endurance',
            'long_run': 'endurance',
            'marathon_pace_run': 'marathon_pace',
            'lactate_threshold': 'lactate_threshold',
            'vo2max': 'vo2max'
        }

        pace_zone = pace_zone_map.get(workout_type, 'general_aerobic')

        return [self.create_executable_step(
            step_order=start_order,
            step_type_id=3,  # INTERVAL (general work)
            step_type_key="interval",
            end_condition_id=3,  # DISTANCE
            end_condition_key="distance",
            end_condition_value=distance_meters,
            target_type=self.get_target_speed_zone(pace_zone)
        )]

    def _estimate_duration(self, workout_data: Dict[str, Any]) -> int:
        """Estimate workout duration in seconds"""
        # Use distance and average pace to estimate
        distance = workout_data.get('distance')
        if distance:
            distance_miles = self.parse_distance(distance)
            # Assume 9 min/mile average pace
            estimated_minutes = distance_miles * 9
            return int(estimated_minutes * 60)

        # Default to 1 hour
        return 3600
