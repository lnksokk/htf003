# Patient Early-Warning System

A simple web-based monitoring system for patient vital signs that alerts healthcare providers when values fall outside normal ranges.

## Features

- **Basic Patient Monitoring**: Display patients with their latest vital signs
- **Real-time Updates**: Automatically refreshes vital signs data
- **Login System**: Authentication for attenders
- **Tiered Alert System**: Tracks abnormal vital signs with warning and critical levels
- **Email Notifications**: Sends emails for critical alerts to attenders and patients
- **Alert Management**: Allows acknowledgment and tracking of notifications

## Quick Start

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the database migration:
   ```
   python migrate_db.py
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Open in browser:
   ```
   http://localhost:5001/
   ```

5. Login with:
   - Username: `attender` / Password: `attenderpassword`

## Vital Sign Thresholds

### Warning Thresholds
- **Heart Rate**: 60-100 bpm
- **SpO₂**: ≥ 95%
- **Temperature**: 36.5-37.5°C

### Critical Thresholds
- **Heart Rate**: 50-120 bpm (values outside this range trigger critical alerts)
- **SpO₂**: ≥ 90% (values below 90% trigger critical alerts)
- **Temperature**: 35.5-38.5°C (values outside this range trigger critical alerts)

## Email Notifications

The system sends email notifications for critical alerts to:
- The assigned attender
- The patient (for critical alerts only, if email is provided)

To configure email sending:
1. Set the following environment variables:
   ```
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=587
   SMTP_USERNAME=your_username
   SMTP_PASSWORD=your_password
   SENDER_EMAIL=hospital@example.com
   ```

## Project Structure

- `app.py`: Main application file
- `models.py`: Database models
- `db.py`: Database configuration
- `utils/`: Utility files for notifications and other functions
- `templates/`: HTML templates
- `migrate_db.py`: Database migration script

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

4. Run database migration:
```
python migrate_db.py
```

5. Create sample data:
```
python sample_data.py
```

6. Run the application:
```
python app.py
```

7. Open your browser and navigate to `http://localhost:5000`

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
- For email notifications in production, configure proper SMTP settings in your environment variables.
- The Vercel deployment uses a serverless approach, which means there are cold starts and limitations on long-running processes.

## Development

The codebase is organized as follows:

- `app.py` - Main Flask application for local development
- `api/index.py` - Entry point for Vercel serverless deployment
- `models.py` - SQLAlchemy data models
- `templates/` - Jinja2 HTML templates
- `utils/` - Utility functions for notifications and other features
- `test_app.py` - Pytest test suite
- `sample_data.py` - Script to generate sample data
- `vercel.json` - Configuration for Vercel deployment
- `migrate_db.py` - Database migration script

## License

MIT 