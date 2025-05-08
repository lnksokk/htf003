from db import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash

class User(db.Model, UserMixin):
    """User data model for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'doctor' or 'nurse'
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Patient(db.Model):
    """Patient data model with vital signs."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    room = db.Column(db.String(20), nullable=False)
    
    # Latest vital signs
    heart_rate = db.Column(db.Integer)
    spo2 = db.Column(db.Float)
    temp = db.Column(db.Float)
    vitals_updated = db.Column(db.DateTime)
    
    # Alert flags
    heart_rate_alert = db.Column(db.Boolean, default=False)
    spo2_alert = db.Column(db.Boolean, default=False)
    temp_alert = db.Column(db.Boolean, default=False)
    
    @property
    def has_alert(self):
        """Return True if any vital sign has an alert."""
        return self.heart_rate_alert or self.spo2_alert or self.temp_alert
    
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