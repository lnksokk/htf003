from flask import Flask, render_template, request, jsonify, redirect, url_for
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
from utils.notifications import send_critical_alert_notification

# Custom Jinja2 filters
@app.template_filter('datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a datetime according to a format string."""
    if value is None:
        return ""
    return value.strftime(format)

# Define vital sign thresholds with warning and critical levels
THRESHOLDS = {
    'heart_rate': {
        'warning': {'min': 60, 'max': 100},
        'critical': {'min': 50, 'max': 120}
    },
    'spo2': {
        'warning': {'min': 95, 'max': 100},
        'critical': {'min': 90, 'max': 100}
    },
    'temp': {
        'warning': {'min': 36.5, 'max': 37.5},
        'critical': {'min': 35.5, 'max': 38.5}
    }
}

@app.route('/')
def index():
    """Redirect to patients page for consistency with main app."""
    return redirect(url_for('dashboard'))

@app.route('/status')
def dashboard():
    """Display the main dashboard with all patients."""
    patients = Patient.query.all()
    now = datetime.now()
    return render_template('dashboard.html', patients=patients, now=now)

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
    has_critical_alert = False
    
    # Check heart rate
    if heart_rate:
        severity = 'normal'
        threshold_str = ""
        
        # Check critical threshold first
        if heart_rate < THRESHOLDS['heart_rate']['critical']['min'] or heart_rate > THRESHOLDS['heart_rate']['critical']['max']:
            severity = 'critical'
            threshold_str = f"{THRESHOLDS['heart_rate']['critical']['min']}-{THRESHOLDS['heart_rate']['critical']['max']}"
            patient_at_risk = True
            has_critical_alert = True
        # Then check warning threshold
        elif heart_rate < THRESHOLDS['heart_rate']['warning']['min'] or heart_rate > THRESHOLDS['heart_rate']['warning']['max']:
            severity = 'warning'
            threshold_str = f"{THRESHOLDS['heart_rate']['warning']['min']}-{THRESHOLDS['heart_rate']['warning']['max']}"
            patient_at_risk = True
        
        # Create alert if not normal
        if severity != 'normal':
            alerts.append(Alert(
                patient_id=patient_id,
                vital_type='heart_rate',
                value=heart_rate,
                threshold=threshold_str,
                severity=severity,
                timestamp=datetime.now(),
                acknowledged=False
            ))
    
    # Check SpO2
    if spo2:
        severity = 'normal'
        threshold_str = ""
        
        # Check critical threshold first
        if spo2 < THRESHOLDS['spo2']['critical']['min']:
            severity = 'critical'
            threshold_str = f">= {THRESHOLDS['spo2']['critical']['min']}"
            patient_at_risk = True
            has_critical_alert = True
        # Then check warning threshold
        elif spo2 < THRESHOLDS['spo2']['warning']['min']:
            severity = 'warning'
            threshold_str = f">= {THRESHOLDS['spo2']['warning']['min']}"
            patient_at_risk = True
        
        # Create alert if not normal
        if severity != 'normal':
            alerts.append(Alert(
                patient_id=patient_id,
                vital_type='spo2',
                value=spo2,
                threshold=threshold_str,
                severity=severity,
                timestamp=datetime.now(),
                acknowledged=False
            ))
    
    # Check temperature
    if temp:
        severity = 'normal'
        threshold_str = ""
        
        # Check critical threshold first
        if temp < THRESHOLDS['temp']['critical']['min'] or temp > THRESHOLDS['temp']['critical']['max']:
            severity = 'critical'
            threshold_str = f"{THRESHOLDS['temp']['critical']['min']}-{THRESHOLDS['temp']['critical']['max']}"
            patient_at_risk = True
            has_critical_alert = True
        # Then check warning threshold
        elif temp < THRESHOLDS['temp']['warning']['min'] or temp > THRESHOLDS['temp']['warning']['max']:
            severity = 'warning'
            threshold_str = f"{THRESHOLDS['temp']['warning']['min']}-{THRESHOLDS['temp']['warning']['max']}"
            patient_at_risk = True
        
        # Create alert if not normal
        if severity != 'normal':
            alerts.append(Alert(
                patient_id=patient_id,
                vital_type='temp',
                value=temp,
                threshold=threshold_str,
                severity=severity,
                timestamp=datetime.now(),
                acknowledged=False
            ))
    
    # Update patient risk status
    patient.current_risk = patient_at_risk
    
    # Add all alerts to the database
    for alert in alerts:
        db.session.add(alert)
    
    db.session.commit()
    
    # Send notifications for critical alerts
    if has_critical_alert:
        for alert in alerts:
            if alert.severity == 'critical':
                send_critical_alert_notification(patient, alert)
                # Mark as notified
                alert.notified = True
        db.session.commit()
    
    # Return the updated patient card HTML fragment
    return render_template('_patient_card.html', patient=patient, vitals=vital)

@app.route('/alerts')
def alerts_queue():
    """Display a queue of all unacknowledged alerts."""
    # Get all unacknowledged alerts, ordered by timestamp (newest first)
    alerts = Alert.query.filter_by(acknowledged=False).order_by(Alert.timestamp.desc()).all()
    
    # Get patient information for each alert
    patients_dict = {}
    for alert in alerts:
        if alert.patient_id not in patients_dict:
            patients_dict[alert.patient_id] = Patient.query.get(alert.patient_id)
    
    now = datetime.now()
    return render_template('alerts.html', alerts=alerts, patients=patients_dict, now=now)

@app.route('/acknowledge_from_queue/<int:alert_id>', methods=['POST'])
def acknowledge_from_queue(alert_id):
    """Acknowledge an alert from the alerts queue."""
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return jsonify({"success": False, "message": "Alert not found"})
    
    # Get patient and vital type information
    patient_id = alert.patient_id
    vital_type = alert.vital_type
    
    # Mark all unacknowledged alerts of the same type for this patient as acknowledged
    related_alerts = Alert.query.filter_by(
        patient_id=patient_id,
        vital_type=vital_type,
        acknowledged=False
    ).all()
    
    for related_alert in related_alerts:
        related_alert.acknowledged = True
    
    # Also clear the corresponding alert flag on the patient
    patient = db.session.get(Patient, patient_id)
    if patient:
        if vital_type == 'heart_rate':
            patient.heart_rate_alert = False
        elif vital_type == 'spo2':
            patient.spo2_alert = False
        elif vital_type == 'temp':
            patient.temp_alert = False
    
    db.session.commit()
    
    # Return success response
    return jsonify({"success": True, "message": f"All alerts for {patient.name} ({vital_type}) acknowledged"})

# Initialize the database when in development mode
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# For Vercel serverless function
# This line is required by Vercel
app.debug = False 