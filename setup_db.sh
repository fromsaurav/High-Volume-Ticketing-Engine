#!/bin/bash
# PostgreSQL Database Setup Script for High-Volume Ticketing Engine

echo "Setting up PostgreSQL database..."

# Variables
DB_NAME="ticketing_db"
DB_USER="ticketing_user"
DB_PASSWORD="ticketing_secure_123"

# Create database and user
sudo -u postgres psql << EOF
-- Drop existing database and user if they exist
DROP DATABASE IF EXISTS ${DB_NAME};
DROP USER IF EXISTS ${DB_USER};

-- Create user
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';

-- Create database
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};

-- Connect to the database and set permissions
\c ${DB_NAME}
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};

EOF

echo ""
echo "Database setup complete!"
echo ""
echo "Update your backend/.env file with:"
echo "  DB_NAME=${DB_NAME}"
echo "  DB_USER=${DB_USER}"
echo "  DB_PASSWORD=${DB_PASSWORD}"
echo "  DB_HOST=localhost"
echo "  DB_PORT=5432"
