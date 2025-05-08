# Patient Early-Warning System

A simple web-based monitoring system for patient vital signs that alerts healthcare providers when values fall outside normal ranges.

## Features

- **Basic Patient Monitoring**: Display patients with their latest vital signs
- **Real-time Updates**: Automatically refreshes vital signs data
- **Login System**: Authentication for doctors and nurses
- **Alerts System**: Tracks abnormal vital signs and allows acknowledgment

## Quick Start

1. Install dependencies:
   ```
   pip install flask flask-sqlalchemy
   ```

2. Run the application:
   ```
   python app.py
   ```

3. Open in browser:
   ```
   http://localhost:5001/
   ```

4. Login with:
   - Username: `doctor` / Password: `doctorpassword`
   - Username: `nurse` / Password: `nursepassword`

## Vital Sign Thresholds

- **Heart Rate**: 60-100 bpm
- **SpO₂**: ≥ 95%
- **Temperature**: 36.5-37.5°C

## Project Structure

- `app.py`: Main application file
- `models.py`: Database models
- `db.py`: Database configuration
- `templates/`: HTML templates

## Tech Stack

- Python 3.12+
- Flask 3.x
- SQLite database with Flask-SQLAlchemy
- Frontend: Jinja2 templates, Bootstrap 5, HTMX 1.9
- No JavaScript frameworks (vanilla JS only where needed)

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/patient-early-warning.git
cd patient-early-warning
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Create sample data:
```
python sample_data.py
```

5. Run the application:
```
python app.py
```

6. Open your browser and navigate to `http://localhost:5000`

## API Endpoints

### Dashboard

- `GET /status` - Returns the main dashboard with all patients
- `GET /status/<patient_id>` - Returns HTMX fragment for a specific patient
- `POST /update` - Receives and processes vital signs data

### Vitals Update Format

To send vital signs data to the system, use the following JSON format:

```json
{
  "patient_id": 1,
  "heart_rate": 75,
  "spo2": 98,
  "temp": 37.0
}
```

## Normal Vital Ranges

- Heart Rate: 60-100 bpm
- SpO₂: ≥ 95%
- Temperature: 36.5-37.5°C

## Running Tests

Run the test suite with pytest:

```
pytest
```

## Deployment

### Deploying to Vercel

1. Install the Vercel CLI:
```
npm install -g vercel
```

2. Login to Vercel:
```
vercel login
```

3. Deploy the project:
```
vercel
```

4. For production deployment:
```
vercel --prod
```

The project is configured with a `vercel.json` file that sets up the Flask application to run as a serverless function. The main entry point is `api/index.py`.

### Important Notes for Vercel Deployment

- SQLite database is not suitable for production on Vercel's serverless environment. For production use, consider using a database service like PostgreSQL or MySQL.
- The Vercel deployment uses a serverless approach, which means there are cold starts and limitations on long-running processes.

## Development

The codebase is organized as follows:

- `app.py` - Main Flask application for local development
- `api/index.py` - Entry point for Vercel serverless deployment
- `models.py` - SQLAlchemy data models
- `templates/` - Jinja2 HTML templates
- `test_app.py` - Pytest test suite
- `sample_data.py` - Script to generate sample data
- `vercel.json` - Configuration for Vercel deployment

## License

MIT 