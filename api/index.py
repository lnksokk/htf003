from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys

# Add the parent directory to the path so we can import from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__, template_folder='../templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')

db = SQLAlchemy(app)

# Import models after db is defined to avoid circular imports
from models import Patient, VitalSign, Alert

# Custom Jinja2 filters
@app.template_filter('datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a datetime according to a format string."""
    if value is None:
        return ""
    return value.strftime(format)

# Define vital sign thresholds
THRESHOLDS = {
    'heart_rate': {'min': 60, 'max': 100},
    'spo2': {'min': 95, 'max': 100},
    'temp': {'min': 36.5, 'max': 37.5}
}

@app.route('/status')
def dashboard():
    """Display the main dashboard with all patients."""
    patients = Patient.query.all()
    return render_template('dashboard.html', patients=patients)

@app.route('/status/<int:patient_id>')
def patient_status(patient_id):
    """Return HTMX fragment for a specific patient."""
    patient = Patient.query.get_or_404(patient_id)
    latest_vitals = VitalSign.query.filter_by(patient_id=patient_id).order_by(VitalSign.timestamp.desc()).first()
    return render_template('_patient_card.html', patient=patient, vitals=latest_vitals)

@app.route('/update', methods=['POST'])
def update_vitals():
    """Receive and process vital signs data, create alerts if thresholds exceeded."""
    data = request.json
    
    patient_id = data.get('patient_id')
    heart_rate = data.get('heart_rate')
    spo2 = data.get('spo2')
    temp = data.get('temp')
    
    # Record the vital signs
    vital = VitalSign(
        patient_id=patient_id,
        heart_rate=heart_rate,
        spo2=spo2,
        temp=temp,
        timestamp=datetime.now()
    )
    db.session.add(vital)
    
    # Check thresholds and create alerts
    alerts = []
    patient = Patient.query.get(patient_id)
    patient_at_risk = False
    
    if heart_rate and (heart_rate < THRESHOLDS['heart_rate']['min'] or heart_rate > THRESHOLDS['heart_rate']['max']):
        alerts.append(Alert(
            patient_id=patient_id,
            vital_type='heart_rate',
            value=heart_rate,
            threshold=f"{THRESHOLDS['heart_rate']['min']}-{THRESHOLDS['heart_rate']['max']}",
            timestamp=datetime.now()
        ))
        patient_at_risk = True
    
    if spo2 and spo2 < THRESHOLDS['spo2']['min']:
        alerts.append(Alert(
            patient_id=patient_id,
            vital_type='spo2',
            value=spo2,
            threshold=f">= {THRESHOLDS['spo2']['min']}",
            timestamp=datetime.now()
        ))
        patient_at_risk = True
    
    if temp and (temp < THRESHOLDS['temp']['min'] or temp > THRESHOLDS['temp']['max']):
        alerts.append(Alert(
            patient_id=patient_id,
            vital_type='temp',
            value=temp,
            threshold=f"{THRESHOLDS['temp']['min']}-{THRESHOLDS['temp']['max']}",
            timestamp=datetime.now()
        ))
        patient_at_risk = True
    
    # Update patient risk status
    patient.current_risk = patient_at_risk
    
    # Add all alerts to the database
    for alert in alerts:
        db.session.add(alert)
    
    db.session.commit()
    
    # Return the updated patient card HTML fragment
    return render_template('_patient_card.html', patient=patient, vitals=vital)

@app.route('/')
def index():
    """Redirect to dashboard."""
    return render_template('dashboard.html', patients=Patient.query.all())

# Initialize the database when in development mode
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# For Vercel serverless function
# This line is required by Vercel
app.debug = False 