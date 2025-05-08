"""
Create sample data for development and testing.

Usage:
    python sample_data.py
"""

from app import app
from db import db
from models import Patient, VitalSign, Alert
from datetime import datetime, timedelta
import random

# Sample patient data
SAMPLE_PATIENTS = [
    {
        "name": "John Doe",
        "room": "101",
        "doctor": "Dr. Smith"
    },
    {
        "name": "Jane Smith",
        "room": "102",
        "doctor": "Dr. Johnson"
    },
    {
        "name": "Robert Brown",
        "room": "103",
        "doctor": "Dr. Williams"
    },
    {
        "name": "Emily Davis",
        "room": "104",
        "doctor": "Dr. Smith"
    },
    {
        "name": "Michael Wilson",
        "room": "105",
        "doctor": "Dr. Johnson"
    }
]

def generate_vitals(patient_id, risk_level=0):
    """Generate random vital signs based on risk level.
    
    Args:
        patient_id: The patient ID
        risk_level: 0=normal, 1=heart rate issue, 2=spo2 issue, 3=temp issue
    
    Returns:
        dict: The vital signs data
    """
    if risk_level == 0:  # Normal vitals
        return {
            "patient_id": patient_id,
            "heart_rate": random.uniform(60, 100),
            "spo2": random.uniform(95, 100),
            "temp": random.uniform(36.5, 37.5)
        }
    elif risk_level == 1:  # Abnormal heart rate
        # Either too high or too low
        heart_rate = random.choice([
            random.uniform(40, 59),  # Too low
            random.uniform(101, 130)  # Too high
        ])
        return {
            "patient_id": patient_id,
            "heart_rate": heart_rate,
            "spo2": random.uniform(95, 100),
            "temp": random.uniform(36.5, 37.5)
        }
    elif risk_level == 2:  # Abnormal SpO2
        return {
            "patient_id": patient_id,
            "heart_rate": random.uniform(60, 100),
            "spo2": random.uniform(85, 94),
            "temp": random.uniform(36.5, 37.5)
        }
    elif risk_level == 3:  # Abnormal temperature
        # Either too high or too low
        temp = random.choice([
            random.uniform(35, 36.4),  # Too low
            random.uniform(37.6, 39)  # Too high
        ])
        return {
            "patient_id": patient_id,
            "heart_rate": random.uniform(60, 100),
            "spo2": random.uniform(95, 100),
            "temp": temp
        }

def create_sample_data():
    """Create sample patients and vital signs data."""
    # Clear existing data
    db.session.query(Alert).delete()
    db.session.query(VitalSign).delete()
    db.session.query(Patient).delete()
    db.session.commit()
    
    # Create patients
    patients = []
    for i, patient_data in enumerate(SAMPLE_PATIENTS):
        patient = Patient(
            name=patient_data["name"],
            room=patient_data["room"],
            doctor=patient_data["doctor"]
        )
        db.session.add(patient)
        patients.append(patient)
    
    db.session.commit()
    
    # Generate vital signs history (past 24 hours)
    now = datetime.now()
    for patient in patients:
        # Generate a series of vitals over the last 24 hours
        for hours_ago in range(24, 0, -1):
            timestamp = now - timedelta(hours=hours_ago)
            
            # Decide whether to generate normal or abnormal vitals
            # Make 2 random patients have abnormal vitals
            if patient.id in [2, 4] and hours_ago < 3:
                risk_level = patient.id % 3 + 1  # 1, 2, or 3 (different abnormalities)
            else:
                risk_level = 0  # Normal vitals
            
            vitals_data = generate_vitals(patient.id, risk_level)
            vital = VitalSign(
                patient_id=patient.id,
                heart_rate=vitals_data["heart_rate"],
                spo2=vitals_data["spo2"],
                temp=vitals_data["temp"],
                timestamp=timestamp
            )
            db.session.add(vital)
    
    # Add current vitals for all patients
    for patient in patients:
        vitals_data = generate_vitals(patient.id)
        vital = VitalSign(
            patient_id=patient.id,
            heart_rate=vitals_data["heart_rate"],
            spo2=vitals_data["spo2"],
            temp=vitals_data["temp"],
            timestamp=now
        )
        db.session.add(vital)
    
    db.session.commit()
    print(f"Created {len(patients)} patients with 24-hour vital history.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_sample_data() 