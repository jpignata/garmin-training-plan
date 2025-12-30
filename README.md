# Garmin Training Plan Scheduler

Automatically schedule marathon training plans (like Pfitzinger 18/55) to your Garmin Connect calendar.

## Overview

This tool takes a structured training plan in YAML format and schedules it to your Garmin Connect account, working backwards from your goal race date. It uses the [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) library to interact with Garmin Connect.

## Features

- 📅 **Smart scheduling** - Works backwards from your race date
- 🏃 **Pfitzinger 18/55 included** - Complete 18-week marathon plan
- ⚡ **Structured workouts** - Properly formatted intervals, tempo runs, and long runs
- 🎯 **Personalized pacing** - Customize all pace zones for your goal time
- 💾 **YAML configuration** - Easy to read and modify training plans

## Quick Start

### Prerequisites

- Python 3.8+
- Garmin Connect account
- pip or pipenv

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/garmin-training-plan.git
cd garmin-training-plan

# Install dependencies
pip install -r requirements.txt

# Set up your Garmin credentials
export GARMIN_EMAIL="your.email@example.com"
export GARMIN_PASSWORD="your_password"
```

### Usage

1. **Customize your training plan** - Edit `plans/pfitz_18_55.yaml`:
   - Set your goal race date
   - Adjust paces for your target time
   - Modify workouts as needed

2. **Schedule to Garmin**:
```bash
python scheduler.py --plan plans/pfitz_18_55.yaml
```

## Training Plan Format

The YAML format supports:

- **Goal event** - Race date and target time
- **Pace zones** - Recovery, easy, marathon pace, tempo, VO2max
- **Structured workouts** - Intervals with warmup/cooldown
- **Flexible distances** - Range-based (e.g., 8-9 miles)
- **Multiple workout types** - Rest, recovery, tempo, intervals, long runs, etc.

See `plans/pfitz_18_55.yaml` for a complete example.

## Project Structure

```
garmin-training-plan/
├── plans/
│   └── pfitz_18_55.yaml       # Pfitzinger 18/55 marathon plan
├── scheduler.py                # Main scheduling script
├── garmin_client.py           # Garmin Connect API wrapper
├── workout_builder.py         # Convert YAML to Garmin workout format
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Roadmap

- [ ] Support for multiple training plans (Hansons, Daniels, etc.)
- [ ] Dry-run mode to preview schedule
- [ ] Delete/update existing workouts
- [ ] Export to other formats (CSV, ICS)
- [ ] Web interface for plan customization

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Pete Pfitzinger for the excellent training plans in "Advanced Marathoning"
- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) for the Garmin API wrapper
- The running community for inspiration and feedback

## Disclaimer

This tool is not affiliated with or endorsed by Garmin or Pete Pfitzinger. Use at your own risk and always consult with a healthcare provider before starting a new training program.
