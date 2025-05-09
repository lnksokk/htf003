from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
import random
from db import db
from models import User, Patient
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

@app.route('/patients')
@login_required
def patients():
    """Display all patients with their vital signs."""
    all_patients = Patient.query.all()
    current_time = datetime.now()
    
    # Only generate new vitals if it's been more than 10 seconds since the last update
    # or if there's an explicit request parameter to generate new vitals
    should_update = request.args.get('generate') == 'true'
    
    for patient in all_patients:
        if not patient.vitals_updated or should_update or \
           (current_time - patient.vitals_updated) > timedelta(seconds=10):
            generate_vitals_for_patient(patient, current_time)
            db.session.add(patient)
    
    if should_update or any(not p.vitals_updated for p in all_patients):
        db.session.commit()
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # Return only the tbody content for HTMX refresh
        return render_template('table_content.html', patients=all_patients, now=current_time)
    
    # Return the full page for normal requests
    return render_template('patients.html', patients=all_patients, now=current_time)

def generate_vitals_for_patient(patient, timestamp):
    """Generate vital signs for a patient."""
    # 30% chance of abnormal vitals
    if random.random() < 0.3:
        # Choose which vital to make abnormal
        risk_type = random.choice(['heart_rate', 'spo2', 'temp'])
        
        if risk_type == 'heart_rate':
            # Either too high or too low heart rate
            patient.heart_rate = random.choice([
                random.randint(40, 59),  # Too low
                random.randint(101, 140)  # Too high
            ])
            patient.heart_rate_alert = True
        else:
            patient.heart_rate = random.randint(60, 100)
            patient.heart_rate_alert = False
            
        if risk_type == 'spo2':
            patient.spo2 = round(random.uniform(85, 94), 1)
            patient.spo2_alert = True
        else:
            patient.spo2 = round(random.uniform(95, 100), 1)
            patient.spo2_alert = False
            
        if risk_type == 'temp':
            patient.temp = round(random.choice([
                random.uniform(35, 36.4),  # Too low
                random.uniform(37.6, 39)   # Too high
            ]), 1)
            patient.temp_alert = True
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

def create_sample_data():
    """Create sample patients and users."""
    # Create users if they don't exist
    if not db.session.query(User).filter_by(username='doctor').first():
        doctor = User(
            username='doctor',
            password_hash=generate_password_hash('doctorpassword'),
            role='doctor'
        )
        db.session.add(doctor)
    
    if not db.session.query(User).filter_by(username='nurse').first():
        nurse = User(
            username='nurse',
            password_hash=generate_password_hash('nursepassword'),
            role='nurse'
        )
        db.session.add(nurse)
    
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