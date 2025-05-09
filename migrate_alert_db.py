"""
Migration script to add the acknowledged field to existing Alert records.

Usage:
    python migrate_alert_db.py
"""

from app import app, db
from models import Alert
import sqlalchemy as sa
from sqlalchemy import inspect

def migrate_alert_table():
    """Add the acknowledged column to the Alert table if it doesn't exist."""
    with app.app_context():
        # Get SQLAlchemy inspector
        inspector = inspect(db.engine)
        
        # Check if Alert table exists
        if 'alert' in inspector.get_table_names():
            # Get existing columns
            columns = [col['name'] for col in inspector.get_columns('alert')]
            
            # Check if acknowledged column exists
            if 'acknowledged' not in columns:
                print("Adding 'acknowledged' column to Alert table...")
                # Add the column using a connection
                with db.engine.connect() as conn:
                    conn.execute(sa.text('ALTER TABLE alert ADD COLUMN acknowledged BOOLEAN DEFAULT 0'))
                    conn.commit()
                print("Column added successfully.")
                
                # Set all existing alerts to acknowledged=True (since they were created before the feature)
                db.session.query(Alert).update({Alert.acknowledged: True})
                db.session.commit()
                print("Set all existing alerts to acknowledged=True")
            else:
                print("'acknowledged' column already exists in Alert table.")
        else:
            print("Alert table doesn't exist yet, no migration needed.")
        
        # Print current schema of the Alert table
        if 'alert' in inspector.get_table_names():
            print("\nCurrent schema of Alert table:")
            for column in inspector.get_columns('alert'):
                print(f"- {column['name']} ({column['type']})")

if __name__ == "__main__":
    migrate_alert_table() 