from db import db
from datetime import datetime

class Patient(db.Model):
    """Patient data model."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    room = db.Column(db.String(20), nullable=False)
    current_risk = db.Column(db.Boolean, default=False)
    
    vitals = db.relationship('VitalSign', backref='patient', lazy=True)
    alerts = db.relationship('Alert', backref='patient', lazy=True)
    
    def __repr__(self):
        return f'<Patient {self.name}>'

class VitalSign(db.Model):
    """Vital signs data model."""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    heart_rate = db.Column(db.Float)
    spo2 = db.Column(db.Float)
    temp = db.Column(db.Float)
    
    def __repr__(self):
        return f'<VitalSign {self.patient_id} @ {self.timestamp}>'

class Alert(db.Model):
    """Alert data model for vital sign threshold violations."""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    vital_type = db.Column(db.String(20), nullable=False)  # heart_rate, spo2, temp
    value = db.Column(db.Float, nullable=False)
    threshold = db.Column(db.String(20), nullable=False)  # e.g., "60-100", ">= 95", "36.5-37.5"
    
    def __repr__(self):
        return f'<Alert {self.vital_type}={self.value} for Patient {self.patient_id}>' 