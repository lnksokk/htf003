from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
import random
from db import db
from models import User, Patient, Alert
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # Use session.get instead of query.get to address SQLAlchemy deprecation warning
    return db.session.get(User, int(user_id))

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

@app.route('/')
def index():
    """Redirect to patients list."""
    return redirect(url_for('patients'))

def generate_fresh_vitals(force_update=False):
    """Generate fresh vitals for all patients if needed.
    
    Returns:
        tuple: (all_patients, current_time, vitals_updated)
        where vitals_updated indicates whether new vitals were generated
    """
    all_patients = Patient.query.all()
    current_time = datetime.now()
    vitals_updated = False
    
    # Determine if we need to update vitals
    # Either forced (via generate=true parameter), 
    # or it's been at least 10 seconds since last update for any patient
    time_threshold_passed = any(not p.vitals_updated or 
                               (current_time - p.vitals_updated) > timedelta(seconds=10) 
                               for p in all_patients)
    
    should_update = force_update or time_threshold_passed
    
    if should_update:
        for patient in all_patients:
            has_alerts = generate_vitals_for_patient(patient, current_time)
            patient.current_risk = has_alerts
            db.session.add(patient)
        db.session.commit()
        vitals_updated = True
    
    return all_patients, current_time, vitals_updated

@app.route('/patients')
@login_required
def patients():
    """Display all patients with their vital signs."""
    # Generate new vitals if needed or requested
    should_update = request.args.get('generate') == 'true'
    all_patients, current_time, _ = generate_fresh_vitals(force_update=should_update)
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # Return only the tbody content for HTMX refresh
        return render_template('table_content.html', patients=all_patients, now=current_time)
    
    # Return the full page for normal requests
    return render_template('patients.html', patients=all_patients, now=current_time)

def generate_vitals_for_patient(patient, timestamp):
    """Generate vital signs for a patient."""
    # Track if any vital sign alerts need to be created
    new_alerts = []
    
    # 30% chance of abnormal vitals
    if random.random() < 0.3:
        # Choose which vital to make abnormal
        risk_type = random.choice(['heart_rate', 'spo2', 'temp'])
        
        if risk_type == 'heart_rate':
            # Either too high or too low heart rate
            heart_rate = random.choice([
                random.randint(40, 59),  # Too low
                random.randint(101, 140)  # Too high
            ])
            patient.heart_rate = heart_rate
            patient.heart_rate_alert = True
            
            # Determine threshold violation and create an alert
            if heart_rate < 60:
                threshold_str = f">= 60"
            else:
                threshold_str = f"<= 100"
            
            new_alerts.append(Alert(
                patient_id=patient.id,
                vital_type='heart_rate',
                value=heart_rate,
                threshold=threshold_str,
                timestamp=timestamp,
                acknowledged=False
            ))
        else:
            patient.heart_rate = random.randint(60, 100)
            patient.heart_rate_alert = False
            
        if risk_type == 'spo2':
            spo2 = round(random.uniform(85, 94), 1)
            patient.spo2 = spo2
            patient.spo2_alert = True
            
            # Create an alert for low SpO2
            new_alerts.append(Alert(
                patient_id=patient.id,
                vital_type='spo2',
                value=spo2,
                threshold=f">= 95",
                timestamp=timestamp,
                acknowledged=False
            ))
        else:
            patient.spo2 = round(random.uniform(95, 100), 1)
            patient.spo2_alert = False
            
        if risk_type == 'temp':
            # Either too high or too low temperature
            temp_choice = random.choice([0, 1])
            if temp_choice == 0:
                temp = round(random.uniform(35, 36.4), 1)  # Too low
                threshold_str = f">= 36.5"
            else:
                temp = round(random.uniform(37.6, 39), 1)  # Too high
                threshold_str = f"<= 37.5"
                
            patient.temp = temp
            patient.temp_alert = True
            
            # Create an alert for abnormal temperature
            new_alerts.append(Alert(
                patient_id=patient.id,
                vital_type='temp',
                value=temp,
                threshold=threshold_str,
                timestamp=timestamp,
                acknowledged=False
            ))
        else:
            patient.temp = round(random.uniform(36.5, 37.5), 1)
            patient.temp_alert = False
    else:
        # Normal vitals
        patient.heart_rate = random.randint(60, 100)
        patient.spo2 = round(random.uniform(95, 100), 1)
        patient.temp = round(random.uniform(36.5, 37.5), 1)
        
        patient.heart_rate_alert = False
        patient.spo2_alert = False
        patient.temp_alert = False
    
    patient.vitals_updated = timestamp
    
    # Add all new alerts to the session
    for alert in new_alerts:
        db.session.add(alert)
    
    # Return whether the patient has any alerts
    return len(new_alerts) > 0

@app.route('/acknowledge/<int:patient_id>/<string:vital_type>', methods=['POST'])
@login_required
def acknowledge_alert(patient_id, vital_type):
    """Acknowledge a vital sign alert."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash('Patient not found', 'danger')
        return redirect(url_for('patients'))
    
    if vital_type == 'heart_rate':
        patient.heart_rate_alert = False
    elif vital_type == 'spo2':
        patient.spo2_alert = False
    elif vital_type == 'temp':
        patient.temp_alert = False
    
    # Also mark any corresponding alerts in the Alert table as acknowledged
    alerts = Alert.query.filter_by(
        patient_id=patient_id, 
        vital_type=vital_type,
        acknowledged=False
    ).all()
    
    for alert in alerts:
        alert.acknowledged = True
    
    db.session.commit()
    
    return redirect(url_for('patients'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('patients'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('patients'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/alerts')
@login_required
def alerts_queue():
    """Display a queue of all unacknowledged alerts."""
    # Generate new vitals if needed to ensure we have the latest alerts
    # Only force update if "generate=true" parameter is present
    force_update = request.args.get('generate') == 'true'
    _, current_time, vitals_updated = generate_fresh_vitals(force_update=force_update)
    
    # Get all unacknowledged alerts, ordered by timestamp (newest first)
    alerts = Alert.query.filter_by(acknowledged=False).order_by(Alert.timestamp.desc()).all()
    
    # Get patient information for each alert
    patients_dict = {}
    for alert in alerts:
        if alert.patient_id not in patients_dict:
            patients_dict[alert.patient_id] = Patient.query.get(alert.patient_id)
    
    # Check if this is a request for just the fragment
    if request.args.get('fragment') == 'true':
        return render_template('_alerts_table.html', alerts=alerts, patients=patients_dict, now=current_time)
    
    return render_template('alerts.html', alerts=alerts, patients=patients_dict, now=current_time)

@app.route('/acknowledge_from_queue/<int:alert_id>', methods=['POST'])
@login_required
def acknowledge_from_queue(alert_id):
    """Acknowledge an alert from the alerts queue."""
    alert = db.session.get(Alert, alert_id)
    if not alert:
        flash('Alert not found', 'danger')
        return redirect(url_for('alerts_queue'))
    
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
    flash(f'Alert for {patient.name} ({vital_type}) acknowledged', 'success')
    
    return redirect(url_for('alerts_queue'))

def create_sample_data():
    """Create sample patients and users."""
    # Create attender user if it doesn't exist
    if not db.session.query(User).filter_by(username='attender').first():
        attender = User(
            username='attender',
            password_hash=generate_password_hash('attenderpassword'),
            role='attender'
        )
        db.session.add(attender)
    
    # Create patients if they don't exist
    if db.session.query(Patient).count() == 0:
        patients = [
            Patient(name="John Smith", room="101"),
            Patient(name="Sarah Johnson", room="102"),
            Patient(name="Michael Williams", room="103"),
            Patient(name="Emma Brown", room="104"),
            Patient(name="James Davis", room="105"),
            Patient(name="Olivia Miller", room="106")
        ]
        
        # Initialize vital signs for each patient
        current_time = datetime.now()
        for patient in patients:
            generate_vitals_for_patient(patient, current_time)
            db.session.add(patient)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    app.run(debug=True, port=5001) 