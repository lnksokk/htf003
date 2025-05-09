"""
Script to check the database structure.
"""

from app import app
from models import Alert, Patient

def check_db():
    """Check the database structure."""
    with app.app_context():
        # Check Alert table
        print("Alert table contents:")
        alerts = Alert.query.all()
        print(f"Total alerts: {len(alerts)}")
        
        for i, alert in enumerate(alerts[:5]):  # Show just the first 5
            print(f"Alert {i+1}:")
            print(f"  Patient ID: {alert.patient_id}")
            print(f"  Vital type: {alert.vital_type}")
            print(f"  Value: {alert.value}")
            print(f"  Acknowledged: {alert.acknowledged}")
        
        # Check Patient table
        patients = Patient.query.all()
        print(f"\nTotal patients: {len(patients)}")
        
        for i, patient in enumerate(patients[:3]):  # Show just the first 3
            print(f"Patient {i+1}: {patient.name}")
            print(f"  Room: {patient.room}")
            print(f"  Heart rate alert: {patient.heart_rate_alert}")
            print(f"  SpO2 alert: {patient.spo2_alert}")
            print(f"  Temp alert: {patient.temp_alert}")

if __name__ == "__main__":
    check_db() 