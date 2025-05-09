"""
Script to clean up users in the database.
Removes doctor/nurse users and ensures only the attender user exists.

Usage:
    python clean_users.py
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def clean_users():
    """Remove doctor/nurse users and ensure only attender user exists."""
    with app.app_context():
        # Delete all users except 'attender'
        db.session.query(User).filter(User.username != 'attender').delete()
        db.session.commit()
        
        # Check if attender exists, create if not
        attender = db.session.query(User).filter_by(username='attender').first()
        if not attender:
            attender = User(
                username='attender',
                password_hash=generate_password_hash('attenderpassword'),
                role='attender'
            )
            db.session.add(attender)
            db.session.commit()
            print("Created attender user")
        else:
            print("Attender user already exists")
            
        # Display all users in the database
        users = User.query.all()
        print(f"Current users in database: {len(users)}")
        for user in users:
            print(f"- {user.username} (role: {user.role})")

if __name__ == "__main__":
    clean_users() 