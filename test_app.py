import pytest
import json
from app import app, THRESHOLDS, db, create_sample_data
from models import Patient, VitalSign, Alert, User
from flask_login import current_user

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            create_sample_data()  # Create sample users and patients
            # Create a test patient
            test_patient = Patient(
                id=1,
                name="Test Patient",
                room="101",
                doctor="Dr. Test",
                current_risk=False
            )
            db.session.add(test_patient)
            db.session.commit()
            yield client
            
            # Clean up after the test
            db.session.remove()
            db.drop_all()

def test_update_normal_vitals(client):
    """Test updating vitals within normal ranges."""
    # Normal vitals data
    vitals_data = {
        "patient_id": 1,
        "heart_rate": 75,
        "spo2": 98,
        "temp": 37.0
    }
    
    # Send POST request to update endpoint
    response = client.post(
        '/update',
        data=json.dumps(vitals_data),
        content_type='application/json'
    )
    
    # Check response
    assert response.status_code == 200
    
    # Check database records
    with app.app_context():
        # Verify vital signs were recorded
        vitals = VitalSign.query.filter_by(patient_id=1).first()
        assert vitals is not None
        assert vitals.heart_rate == 75
        assert vitals.spo2 == 98
        assert vitals.temp == 37.0
        
        # Verify no alerts were created
        alerts = Alert.query.filter_by(patient_id=1).all()
        assert len(alerts) == 0
        
        # Verify patient is not at risk
        patient = Patient.query.get(1)
        assert patient.current_risk is False

def test_update_abnormal_heart_rate(client):
    """Test updating vitals with abnormal heart rate."""
    # Abnormal vitals data (high heart rate)
    vitals_data = {
        "patient_id": 1,
        "heart_rate": 120,  # Above normal range
        "spo2": 98,
        "temp": 37.0
    }
    
    # Send POST request to update endpoint
    response = client.post(
        '/update',
        data=json.dumps(vitals_data),
        content_type='application/json'
    )
    
    # Check response
    assert response.status_code == 200
    
    # Check database records
    with app.app_context():
        # Verify vital signs were recorded
        vitals = VitalSign.query.filter_by(patient_id=1).first()
        assert vitals is not None
        assert vitals.heart_rate == 120
        
        # Verify alert was created
        alerts = Alert.query.filter_by(patient_id=1).all()
        assert len(alerts) == 1
        assert alerts[0].vital_type == "heart_rate"
        assert alerts[0].value == 120
        assert alerts[0].threshold == f"{THRESHOLDS['heart_rate']['min']}-{THRESHOLDS['heart_rate']['max']}"
        
        # Verify patient is at risk
        patient = Patient.query.get(1)
        assert patient.current_risk is True

def test_update_abnormal_spo2(client):
    """Test updating vitals with abnormal SpO2."""
    # Abnormal vitals data (low SpO2)
    vitals_data = {
        "patient_id": 1,
        "heart_rate": 75,
        "spo2": 92,  # Below normal range
        "temp": 37.0
    }
    
    # Send POST request to update endpoint
    response = client.post(
        '/update',
        data=json.dumps(vitals_data),
        content_type='application/json'
    )
    
    # Check database records
    with app.app_context():
        # Verify alert was created
        alerts = Alert.query.filter_by(patient_id=1).all()
        assert len(alerts) == 1
        assert alerts[0].vital_type == "spo2"
        
        # Verify patient is at risk
        patient = Patient.query.get(1)
        assert patient.current_risk is True

def test_update_abnormal_temperature(client):
    """Test updating vitals with abnormal temperature."""
    # Abnormal vitals data (high temperature)
    vitals_data = {
        "patient_id": 1,
        "heart_rate": 75,
        "spo2": 98,
        "temp": 38.5  # Above normal range
    }
    
    # Send POST request to update endpoint
    response = client.post(
        '/update',
        data=json.dumps(vitals_data),
        content_type='application/json'
    )
    
    # Check database records
    with app.app_context():
        # Verify alert was created
        alerts = Alert.query.filter_by(patient_id=1).all()
        assert len(alerts) == 1
        assert alerts[0].vital_type == "temp"
        
        # Verify patient is at risk
        patient = Patient.query.get(1)
        assert patient.current_risk is True

def test_multiple_abnormal_vitals(client):
    """Test updating multiple abnormal vitals."""
    # Multiple abnormal vitals
    vitals_data = {
        "patient_id": 1,
        "heart_rate": 120,  # Above normal range
        "spo2": 92,         # Below normal range
        "temp": 38.5        # Above normal range
    }
    
    # Send POST request to update endpoint
    response = client.post(
        '/update',
        data=json.dumps(vitals_data),
        content_type='application/json'
    )
    
    # Check database records
    with app.app_context():
        # Verify all alerts were created
        alerts = Alert.query.filter_by(patient_id=1).all()
        assert len(alerts) == 3
        
        # Verify patient is at risk
        patient = Patient.query.get(1)
        assert patient.current_risk is True

def test_login_success(client):
    """Test successful login."""
    response = client.post('/login', data={
        'username': 'doctor',
        'password': 'doctorpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Patient Monitoring' in response.data

def test_login_failure(client):
    """Test failed login with wrong password."""
    response = client.post('/login', data={
        'username': 'doctor',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data

def test_patients_listing(client):
    """Test patients listing page."""
    # Login first
    client.post('/login', data={'username': 'doctor', 'password': 'doctorpassword'})
    
    # Access the patients page
    response = client.get('/patients')
    
    assert response.status_code == 200
    assert b'Patient Monitoring' in response.data
    assert b'John Smith' in response.data
    assert b'Heart Rate' in response.data
    assert b'SpO' in response.data
    assert b'Temperature' in response.data

def test_alert_highlighting(client):
    """Test alert highlighting and acknowledgment."""
    # Login
    client.post('/login', data={'username': 'doctor', 'password': 'doctorpassword'})
    
    # Create a patient with an alert
    with app.app_context():
        patient = Patient.query.first()
        patient.heart_rate = 120  # Abnormal heart rate
        patient.heart_rate_alert = True
        db.session.commit()
        
    # Check if the alert is shown
    response = client.get('/patients')
    assert b'vital-warning' in response.data
    assert b'Alert' in response.data
    
    # Acknowledge the alert
    client.post(f'/acknowledge/{patient.id}/heart_rate')
    
    # Verify the alert was acknowledged
    with app.app_context():
        patient = Patient.query.first()
        assert not patient.heart_rate_alert

def test_access_control(client):
    """Test that unauthorized users can't access patients page."""
    # Without login
    response = client.get('/patients', follow_redirects=True)
    
    # Should redirect to login page
    assert b'Login' in response.data
    assert b'Username' in response.data 