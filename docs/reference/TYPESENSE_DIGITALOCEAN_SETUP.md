# Self-Hosting Typesense on DigitalOcean

**Cost**: $6/month (vs $22/month for Typesense Cloud)
**Time**: ~20 minutes setup

---

## Step 1: Create a DigitalOcean Droplet (5 minutes)

1. Log in to [DigitalOcean](https://cloud.digitalocean.com)
2. Click **"Create"** → **"Droplets"**
3. Configure:
   - **Image**: Ubuntu 22.04 (LTS) x64
   - **Plan**: Basic
   - **CPU options**: Regular Intel/AMD - $6/month
     - 1 GB RAM / 1 vCPU / 25 GB SSD
   - **Datacenter region**: Choose closest to your users (e.g., New York, San Francisco)
   - **Authentication**: SSH key (recommended) or Password
   - **Hostname**: `typesense-server`
4. Click **"Create Droplet"**
5. Wait ~1 minute for droplet to be ready
6. **Copy the IP address** (e.g., `165.227.123.45`)

---

## Step 2: SSH into Your Droplet

```bash
# Replace with your droplet's IP
ssh root@YOUR_DROPLET_IP

# If using password, enter it when prompted
```

---

## Step 3: Install Typesense (5 minutes)

Once connected via SSH, run these commands:

### 3.1: Update System
```bash
apt update && apt upgrade -y
```

### 3.2: Download and Install Typesense
```bash
# Download Typesense (latest version)
wget https://dl.typesense.org/releases/27.1/typesense-server-27.1-linux-amd64.tar.gz

# Extract
tar -xzf typesense-server-27.1-linux-amd64.tar.gz

# Move to /usr/local/bin
mv typesense-server /usr/local/bin/

# Make it executable
chmod +x /usr/local/bin/typesense-server

# Verify installation
typesense-server --version
```

### 3.3: Create Data Directory
```bash
mkdir -p /var/lib/typesense
```

### 3.4: Generate API Key
```bash
# Generate a secure random API key
openssl rand -base64 32
```

**Save this API key!** You'll need it for your `.env` file.

Example output: `xK9mP2nL5qR8sT1vW3yZ6aC4bD7eF0gH1iJ2kM5nP8=`

---

## Step 4: Configure Typesense as a Service (5 minutes)

### 4.1: Create Systemd Service File
```bash
nano /etc/systemd/system/typesense.service
```

### 4.2: Paste This Configuration
```ini
[Unit]
Description=Typesense Search Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/lib/typesense
ExecStart=/usr/local/bin/typesense-server \
  --data-dir=/var/lib/typesense \
  --api-key=YOUR_GENERATED_API_KEY_HERE \
  --api-port=8108 \
  --enable-cors
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Important**: Replace `YOUR_GENERATED_API_KEY_HERE` with the API key from step 3.4

**Save**: Press `Ctrl+X`, then `Y`, then `Enter`

### 4.3: Start Typesense
```bash
# Reload systemd
systemctl daemon-reload

# Enable Typesense to start on boot
systemctl enable typesense

# Start Typesense
systemctl start typesense

# Check status
systemctl status typesense
```

You should see `active (running)` in green.

---

## Step 5: Configure Firewall (3 minutes)

```bash
# Install UFW (Uncomplicated Firewall)
apt install ufw -y

# Allow SSH (important! don't lock yourself out)
ufw allow 22/tcp

# Allow Typesense port
ufw allow 8108/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

---

## Step 6: Test Typesense (2 minutes)

### 6.1: From Your Droplet (SSH)
```bash
curl http://localhost:8108/health
```

Should return: `{"ok":true}`

### 6.2: From Your Local Machine
```bash
# Replace with your droplet IP and API key
curl http://YOUR_DROPLET_IP:8108/health \
  -H "X-TYPESENSE-API-KEY: YOUR_API_KEY"
```

Should return: `{"ok":true}`

---

## Step 7: Update Your .env File

Update your local `.env` file:

```bash
# OLD (local Docker)
# TYPESENSE_HOST=localhost
# TYPESENSE_PORT=8108
# TYPESENSE_PROTOCOL=http

# NEW (DigitalOcean)
TYPESENSE_HOST=YOUR_DROPLET_IP
TYPESENSE_PORT=8108
TYPESENSE_PROTOCOL=http
TYPESENSE_API_KEY=YOUR_GENERATED_API_KEY
```

---

## Step 8: Index Your Products

```bash
# Run indexer with new Typesense server
python src/indexer_neon.py
```

This will populate your DigitalOcean-hosted Typesense with all 34k products (~35-45 minutes).

---

## Step 9: Test Your Search

```bash
# Start your Flask app
python src/app.py

# In another terminal, test search
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sterile gloves under $50"}'
```

Should return search results!

---

## Optional: Set Up SSL/HTTPS (Recommended for Production)

For production, you should use HTTPS. Here's how:

### Option A: Use Nginx Reverse Proxy with Let's Encrypt

```bash
# Install Nginx
apt install nginx certbot python3-certbot-nginx -y

# Create Nginx config
nano /etc/nginx/sites-available/typesense
```

Paste:
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://localhost:8108;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
ln -s /etc/nginx/sites-available/typesense /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

If you have a domain, get SSL:
```bash
certbot --nginx -d your-domain.com
```

Then update `.env`:
```bash
TYPESENSE_HOST=your-domain.com
TYPESENSE_PORT=443
TYPESENSE_PROTOCOL=https
```

### Option B: Keep HTTP (Simpler, OK for Testing)

If your backend and Typesense are on the same internal network, HTTP is fine.

---

## Deployment with DigitalOcean Typesense

When deploying to Render/Vercel, use these environment variables:

```bash
TYPESENSE_HOST=YOUR_DROPLET_IP  # or domain if you set up Nginx
TYPESENSE_PORT=8108             # or 443 if using HTTPS
TYPESENSE_PROTOCOL=http         # or https if using SSL
TYPESENSE_API_KEY=YOUR_GENERATED_API_KEY
```

---

## Maintenance & Monitoring

### Check Typesense Status
```bash
ssh root@YOUR_DROPLET_IP
systemctl status typesense
```

### View Typesense Logs
```bash
journalctl -u typesense -f
```

### Restart Typesense
```bash
systemctl restart typesense
```

### Update Typesense (when new version releases)
```bash
# Download new version (check https://typesense.org/downloads/ for latest)
wget https://dl.typesense.org/releases/NEW_VERSION/typesense-server-NEW_VERSION-linux-amd64.tar.gz

# Stop service
systemctl stop typesense

# Replace binary
tar -xzf typesense-server-NEW_VERSION-linux-amd64.tar.gz
mv typesense-server /usr/local/bin/

# Start service
systemctl start typesense
```

### Monitor Resource Usage
```bash
# CPU and RAM usage
htop

# Or simpler
top

# Disk space
df -h
```

### Backup Data
```bash
# Backup Typesense data directory
tar -czf typesense-backup-$(date +%Y%m%d).tar.gz /var/lib/typesense

# Download to local machine
scp root@YOUR_DROPLET_IP:~/typesense-backup-*.tar.gz ./
```

---

## Cost Breakdown

| Item | Cost |
|------|------|
| DigitalOcean Droplet (1GB) | $6/month |
| Bandwidth (1TB included) | $0 |
| **Total** | **$6/month** |

**vs Typesense Cloud**: $22/month
**Savings**: $16/month ($192/year)

---

## Troubleshooting

### Typesense won't start
```bash
# Check logs
journalctl -u typesense -n 50

# Common issues:
# 1. API key has special characters - wrap in quotes in service file
# 2. Port 8108 already in use - check with: netstat -tlnp | grep 8108
# 3. Permission issues - check: ls -la /var/lib/typesense
```

### Can't connect from local machine
```bash
# Check firewall
ufw status

# Make sure port 8108 is allowed
ufw allow 8108/tcp
```

### Out of memory
```bash
# Check memory usage
free -h

# If needed, add swap space (2GB example)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Search is slow
```bash
# Check CPU/RAM usage
htop

# Consider upgrading to 2GB droplet ($12/month)
# Or optimize your Typesense schema
```

---

## Security Best Practices

1. **Change default SSH port** (optional but recommended)
2. **Use SSH keys** instead of password
3. **Keep system updated**: `apt update && apt upgrade -y`
4. **Use strong API key**: Already done in step 3.4
5. **Enable automatic security updates**:
   ```bash
   apt install unattended-upgrades -y
   dpkg-reconfigure -plow unattended-upgrades
   ```
6. **Monitor logs regularly**: `journalctl -u typesense -f`

---

## Quick Command Reference

```bash
# Start Typesense
systemctl start typesense

# Stop Typesense
systemctl stop typesense

# Restart Typesense
systemctl restart typesense

# Check status
systemctl status typesense

# View logs
journalctl -u typesense -f

# Test health
curl http://localhost:8108/health
```

---

## When to Upgrade?

**Upgrade to 2GB RAM ($12/month) if:**
- Search latency > 500ms consistently
- Memory usage > 80%
- You're adding more products (100k+)

**Current setup (1GB) is perfect for:**
- ✅ 34,000 products
- ✅ Moderate traffic (hundreds of searches/day)
- ✅ Development and testing
- ✅ Small to medium production apps

---

## Support

**Typesense Documentation**: https://typesense.org/docs/
**DigitalOcean Docs**: https://docs.digitalocean.com/
**Community**: https://github.com/typesense/typesense/discussions

---

**You're now running Typesense on DigitalOcean!** 🚀

**Total setup cost**: $6/month (vs $22/month for Typesense Cloud)
