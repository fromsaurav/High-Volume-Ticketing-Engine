#!/bin/bash
# Fix PostgreSQL Authentication 

echo "=== Fixing PostgreSQL Authentication ==="
echo ""

echo "Step 1: Backing up pg_hba.conf..."
sudo cp /etc/postgresql/16/main/pg_hba.conf /etc/postgresql/16/main/pg_hba.conf.backup.$(date +%s)

echo "Step 2: Updating pg_hba.conf to use peer authentication for postgres user..."
sudo bash -c 'cat > /etc/postgresql/16/main/pg_hba.conf << EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5
EOF'

echo "Step 3: Reloading PostgreSQL..."
sudo systemctl reload postgresql

sleep 2

echo "Step 4: Setting postgres password..."
sudo -u postgres psql << EOF
ALTER USER postgres WITH PASSWORD 'root123';
CREATE DATABASE IF NOT EXISTS ticketing_db;
DROP USER IF EXISTS ticketing_user;
CREATE USER ticketing_user WITH PASSWORD 'ticketing_secure_123';
GRANT ALL PRIVILEGES ON DATABASE ticketing_db TO ticketing_user;
\c ticketing_db
GRANT ALL ON SCHEMA public TO ticketing_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ticketing_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ticketing_user;
EOF

echo ""
echo "✅ PostgreSQL configured successfully!"
echo "   - Database: ticketing_db"
echo "   - User: postgres (password: root123)"
echo "   - User: ticketing_user (password: ticketing_secure_123)"
echo ""
