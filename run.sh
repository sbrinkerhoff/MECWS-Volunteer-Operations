#!/bin/bash
# run.sh - Helper script to setup and run the app

# Check if .venv exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Initialize DB if it doesn't exist (basic check for migrations)
# Always ensure the database is up to date
echo "Running database migrations..."
flask db upgrade

# Attempt to seed the database (safe to run multiple times, checks for existing data)
echo "Seeding database (if empty)..."
python seed_db.py

# Run the app
echo "Starting Flask app..."
flask run --port 5001
