from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime
import os
import random
from db import db
from models import Patient, VitalSign, Alert
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')

# Initialize the db with the app
db.init_app(app)

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

# Mock users (in a real app, this would be in the database)
USERS = {
    'nurse': {
        'password': generate_password_hash('nursepassword'),
        'role': 'nurse'
    },
    'doctor': {
        'password': generate_password_hash('doctorpassword'),
        'role': 'doctor'
    }
}

# Helper function to generate random vitals for a patient
def generate_random_vitals(patient_id, risk_level=0):
    """Generate random vital signs based on risk level."""
    if risk_level == 0:  # Normal vitals
        return {
            "patient_id": patient_id,
            "heart_rate": round(random.uniform(60, 100)),
            "spo2": round(random.uniform(95, 100), 1),
            "temp": round(random.uniform(36.5, 37.5), 1)
        }
    elif risk_level == 1:  # Abnormal heart rate
        # Either too high or too low
        heart_rate = random.choice([
            round(random.uniform(40, 59)),  # Too low
            round(random.uniform(101, 130))  # Too high
        ])
        return {
            "patient_id": patient_id,
            "heart_rate": heart_rate,
            "spo2": round(random.uniform(95, 100), 1),
            "temp": round(random.uniform(36.5, 37.5), 1)
        }
    elif risk_level == 2:  # Abnormal SpO2
        return {
            "patient_id": patient_id,
            "heart_rate": round(random.uniform(60, 100)),
            "spo2": round(random.uniform(85, 94), 1),
            "temp": round(random.uniform(36.5, 37.5), 1)
        }
    elif risk_level == 3:  # Abnormal temperature
        # Either too high or too low
        temp = random.choice([
            round(random.uniform(35, 36.4), 1),  # Too low
            round(random.uniform(37.6, 39), 1)  # Too high
        ])
        return {
            "patient_id": patient_id,
            "heart_rate": round(random.uniform(60, 100)),
            "spo2": round(random.uniform(95, 100), 1),
            "temp": temp
        }

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/status')
@login_required
def dashboard():
    """Display the main dashboard with all patients."""
    # Get all patients
    patients = Patient.query.all()
    
    # Add latest vitals for each patient
    for patient in patients:
        latest_vitals = VitalSign.query.filter_by(patient_id=patient.id).order_by(VitalSign.timestamp.desc()).first()
        if latest_vitals:
            patient.latest_vitals = latest_vitals
    
    # Return the full dashboard page with current time
    now = datetime.now()
    return render_template('dashboard.html', patients=patients, now=now)

@app.route('/refresh-data')
@login_required
def refresh_data():
    """Generate new vital signs data for all patients."""
    patients = Patient.query.all()
    current_time = datetime.now()
    
    for patient in patients:
        # Decide on risk level randomly
        risk_level = random.choices([0, 1, 2, 3], weights=[0.7, 0.1, 0.1, 0.1])[0]
        
        # Generate new vitals
        vital_data = generate_random_vitals(patient.id, risk_level)
        
        # Create and save new vital signs
        vital = VitalSign(
            patient_id=patient.id,
            heart_rate=vital_data["heart_rate"],
            spo2=vital_data["spo2"],
            temp=vital_data["temp"],
            timestamp=current_time
        )
        db.session.add(vital)
        
        # Create alerts for abnormal values
        patient_at_risk = False
        
        # Check heart rate
        if vital_data["heart_rate"] < THRESHOLDS['heart_rate']['min'] or vital_data["heart_rate"] > THRESHOLDS['heart_rate']['max']:
            alert = Alert(
                patient_id=patient.id,
                vital_type='heart_rate',
                value=vital_data["heart_rate"],
                threshold=f"{THRESHOLDS['heart_rate']['min']}-{THRESHOLDS['heart_rate']['max']}",
                timestamp=current_time
            )
            db.session.add(alert)
            patient_at_risk = True
        
        # Check SpO2
        if vital_data["spo2"] < THRESHOLDS['spo2']['min']:
            alert = Alert(
                patient_id=patient.id,
                vital_type='spo2',
                value=vital_data["spo2"],
                threshold=f">= {THRESHOLDS['spo2']['min']}",
                timestamp=current_time
            )
            db.session.add(alert)
            patient_at_risk = True
        
        # Check temperature
        if vital_data["temp"] < THRESHOLDS['temp']['min'] or vital_data["temp"] > THRESHOLDS['temp']['max']:
            alert = Alert(
                patient_id=patient.id,
                vital_type='temp',
                value=vital_data["temp"],
                threshold=f"{THRESHOLDS['temp']['min']}-{THRESHOLDS['temp']['max']}",
                timestamp=current_time
            )
            db.session.add(alert)
            patient_at_risk = True
        
        # Update patient risk status
        if patient_at_risk:
            patient.current_risk = True
    
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/status/<int:patient_id>')
@login_required
def patient_status(patient_id):
    """Return HTMX fragment for a specific patient."""
    patient = Patient.query.get_or_404(patient_id)
    latest_vitals = VitalSign.query.filter_by(patient_id=patient_id).order_by(VitalSign.timestamp.desc()).first()
    
    # Attach the latest vitals to the patient object
    if latest_vitals:
        patient.latest_vitals = latest_vitals
    
    return render_template('_patient_card.html', patient=patient)

@app.route('/alerts')
@login_required
def alerts():
    """Display all alerts."""
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    now = datetime.now()
    return render_template('alerts.html', alerts=alerts, now=now)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and check_password_hash(USERS[username]['password'], password):
            session['username'] = username
            session['role'] = USERS[username]['role']
            flash('You were successfully logged in', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('username', None)
    session.pop('role', None)
    flash('You were successfully logged out', 'success')
    return redirect(url_for('login'))

@app.route('/acknowledge-alert/<int:alert_id>', methods=['POST', 'GET'])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge and remove an alert."""
    alert = Alert.query.get_or_404(alert_id)
    patient_id = alert.patient_id
    
    # Delete the alert
    db.session.delete(alert)
    db.session.commit()
    
    # Check if the patient has other active alerts
    remaining_alerts = Alert.query.filter_by(patient_id=patient_id).count()
    
    # If no alerts remain, set the patient's risk status to false
    if remaining_alerts == 0:
        patient = Patient.query.get(patient_id)
        if patient:
            patient.current_risk = False
            db.session.commit()
    
    return redirect(url_for('alerts'))

@app.route('/api/generate-vitals')
@login_required
def api_generate_vitals():
    """API endpoint to generate new vital signs data for all patients."""
    patients = Patient.query.all()
    current_time = datetime.now()
    
    # Update all patients at once for consistency
    updates = []
    
    for patient in patients:
        # Decide on risk level randomly
        risk_level = random.choices([0, 1, 2, 3], weights=[0.7, 0.1, 0.1, 0.1])[0]
        
        # Generate new vitals
        vital_data = generate_random_vitals(patient.id, risk_level)
        
        # Create and save new vital signs
        vital = VitalSign(
            patient_id=patient.id,
            heart_rate=vital_data["heart_rate"],
            spo2=vital_data["spo2"],
            temp=vital_data["temp"],
            timestamp=current_time
        )
        db.session.add(vital)
        
        # Create alerts for abnormal values
        patient_at_risk = False
        
        # Check heart rate
        if vital_data["heart_rate"] < THRESHOLDS['heart_rate']['min'] or vital_data["heart_rate"] > THRESHOLDS['heart_rate']['max']:
            alert = Alert(
                patient_id=patient.id,
                vital_type='heart_rate',
                value=vital_data["heart_rate"],
                threshold=f"{THRESHOLDS['heart_rate']['min']}-{THRESHOLDS['heart_rate']['max']}",
                timestamp=current_time
            )
            db.session.add(alert)
            patient_at_risk = True
        
        # Check SpO2
        if vital_data["spo2"] < THRESHOLDS['spo2']['min']:
            alert = Alert(
                patient_id=patient.id,
                vital_type='spo2',
                value=vital_data["spo2"],
                threshold=f">= {THRESHOLDS['spo2']['min']}",
                timestamp=current_time
            )
            db.session.add(alert)
            patient_at_risk = True
        
        # Check temperature
        if vital_data["temp"] < THRESHOLDS['temp']['min'] or vital_data["temp"] > THRESHOLDS['temp']['max']:
            alert = Alert(
                patient_id=patient.id,
                vital_type='temp',
                value=vital_data["temp"],
                threshold=f"{THRESHOLDS['temp']['min']}-{THRESHOLDS['temp']['max']}",
                timestamp=current_time
            )
            db.session.add(alert)
            patient_at_risk = True
        
        # Update patient risk status
        if patient_at_risk:
            patient.current_risk = True
            
        updates.append(patient.id)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "updates": updates,
        "timestamp": current_time.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/')
def index():
    """Redirect to dashboard."""
    return redirect(url_for('dashboard'))

# Create sample data
def create_sample_data():
    """Create sample data for the application."""
    # Check if we already have data
    if Patient.query.count() > 0:
        return
    
    # Create some patients
    patients = [
        Patient(name="John Smith", room="101"),
        Patient(name="Sarah Johnson", room="102"),
        Patient(name="Michael Williams", room="103"),
        Patient(name="Emma Brown", room="104"),
        Patient(name="James Davis", room="105"),
        Patient(name="Olivia Miller", room="106")
    ]
    
    for patient in patients:
        db.session.add(patient)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    app.run(debug=True, port=5001) 