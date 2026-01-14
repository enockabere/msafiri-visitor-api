# Fix External API Access Issue

## Problem
- API works on `localhost:8000` ✅
- API crashes ("Killed") when accessed via `41.90.17.25:8000` ❌
- Admin portal gets 500 errors after login

## Root Cause
The "Killed" message indicates the process is being terminated, likely due to:
1. **Out of Memory (OOM)** - Most common cause
2. **Firewall blocking external connections**
3. **Gunicorn worker timeout**

## Solution Steps

### Step 1: Check Memory Usage
```bash
# Check available memory
free -h

# Check if OOM killer is active
dmesg | grep -i "killed process"

# Monitor memory while starting API
htop
```

### Step 2: Reduce Gunicorn Workers (If Memory Issue)
Edit `gunicorn.conf.py`:
```python
import os

bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"
workers = 1  # Reduce from 4 to 1 if low memory
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 100  # Reduce from 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120  # Add timeout
preload_app = True
```

### Step 3: Check Firewall Rules
```bash
# Check if port 8000 is open
sudo ufw status

# If firewall is active, allow port 8000
sudo ufw allow 8000/tcp

# Check iptables
sudo iptables -L -n | grep 8000
```

### Step 4: Test API Startup
```bash
# Stop existing API
pkill -f gunicorn
pkill -f uvicorn

# Start with single worker and debug logging
cd ~/projects/msafiri/msf-msafiri-visitor-api
gunicorn app.main:app -c gunicorn.conf.py --log-level debug

# In another terminal, test external access
curl http://41.90.17.25:8000/health
```

### Step 5: Alternative - Use Uvicorn Directly (Lower Memory)
```bash
# Stop gunicorn
pkill -f gunicorn

# Start with uvicorn (uses less memory)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Step 6: Check System Logs
```bash
# Check for OOM killer messages
sudo journalctl -xe | grep -i "killed"

# Check API logs
tail -f ~/projects/msafiri/msf-msafiri-visitor-api/logs/*.log
```

## Quick Fix (Recommended)

### Option A: Use PM2 with Lower Memory
```bash
# Install PM2 if not installed
npm install -g pm2

# Create PM2 config
cat > ~/projects/msafiri/msf-msafiri-visitor-api/ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'msafiri-api',
    script: 'uvicorn',
    args: 'app.main:app --host 0.0.0.0 --port 8000',
    cwd: '/home/leo-server/projects/msafiri/msf-msafiri-visitor-api',
    instances: 1,
    exec_mode: 'fork',
    max_memory_restart: '500M',
    env: {
      PORT: 8000,
      ENVIRONMENT: 'production'
    }
  }]
}
EOF

# Start with PM2
cd ~/projects/msafiri/msf-msafiri-visitor-api
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Option B: Use Systemd Service
```bash
# Create systemd service
sudo tee /etc/systemd/system/msafiri-api.service << 'EOF'
[Unit]
Description=MSafiri Visitor API
After=network.target postgresql.service

[Service]
Type=simple
User=leo-server
WorkingDirectory=/home/leo-server/projects/msafiri/msf-msafiri-visitor-api
Environment="PATH=/home/leo-server/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PORT=8000"
Environment="ENVIRONMENT=production"
ExecStart=/home/leo-server/.local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10
StandardOutput=append:/var/log/msafiri-api.log
StandardError=append:/var/log/msafiri-api-error.log

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable msafiri-api
sudo systemctl start msafiri-api
sudo systemctl status msafiri-api
```

## Verify Fix
```bash
# Test from server
curl http://localhost:8000/health

# Test from external
curl http://41.90.17.25:8000/health

# Should return:
# {"status":"healthy","environment":"production","database":"connected",...}
```

## Update Admin Portal .env
Once API is accessible externally, your current `.env.production` should work:
```bash
NEXT_PUBLIC_API_URL=http://41.90.17.25:8000
NEXTAUTH_URL=http://41.90.17.25:3000/portal
```

## Troubleshooting

### If still getting "Killed"
1. **Check memory**: `free -h` - If < 500MB free, upgrade server or reduce workers
2. **Check swap**: `swapon --show` - Add swap if none exists
3. **Check logs**: `dmesg | tail -50` - Look for OOM messages

### If connection refused
1. **Check firewall**: `sudo ufw status`
2. **Check if API is running**: `ps aux | grep uvicorn`
3. **Check port binding**: `sudo netstat -tlnp | grep 8000`

### If 500 errors persist
1. **Check API logs**: `tail -f /var/log/msafiri-api.log`
2. **Test API directly**: `curl -v http://41.90.17.25:8000/api/v1/profile/me -H "Authorization: Bearer YOUR_TOKEN"`
3. **Check database connection**: Ensure PostgreSQL is accessible

## Next Steps
After fixing API external access:
1. Restart Next.js admin portal
2. Clear browser cache
3. Try logging in again
4. Check browser console for errors
