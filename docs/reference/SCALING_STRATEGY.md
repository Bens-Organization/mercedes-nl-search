# Scaling Strategy for Multi-Client Typesense

This guide covers how to scale your Typesense infrastructure as you grow to multiple clients.

---

## Current Setup Capacity

**Your current setup (1GB DigitalOcean droplet):**
- ✅ 1 collection, 34k products (Mercedes Scientific)
- ✅ Can handle 2-4 similar clients comfortably (~100-150k total products)
- ✅ Monthly cost: $6

---

## Multi-Tenant Architecture Options

### Option 1: Single Typesense Server, Multiple Collections (Shared Resources)

**How it works:**
```
┌─────────────────────────────────┐
│  Typesense Server (1GB)         │
│  ┌────────────────────────────┐ │
│  │ Collection: client_1       │ │  34k products
│  │ Collection: client_2       │ │  40k products
│  │ Collection: client_3       │ │  25k products
│  └────────────────────────────┘ │
└─────────────────────────────────┘
```

**Pros:**
- ✅ Cheapest option ($6/month for small scale)
- ✅ Easy to manage (one server)
- ✅ Simple deployment

**Cons:**
- ❌ All clients share resources
- ❌ One client's heavy queries affect all others
- ❌ Limited by single server capacity
- ❌ All clients down if server fails

**Best for:**
- 2-5 small clients
- Total < 200k products
- Low to moderate query volume

**Capacity:**
| Droplet Size | Products | Clients (avg 30k each) | Cost |
|--------------|----------|------------------------|------|
| 1GB RAM | ~150k | ~5 | $6/month |
| 2GB RAM | ~300k | ~10 | $12/month |
| 4GB RAM | ~600k | ~20 | $24/month |
| 8GB RAM | ~1.2M | ~40 | $48/month |

---

### Option 2: Dedicated Server Per Client (Isolated Resources)

**How it works:**
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Client 1 Server │  │ Client 2 Server │  │ Client 3 Server │
│ (1GB - $6)      │  │ (1GB - $6)      │  │ (1GB - $6)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Pros:**
- ✅ Complete isolation
- ✅ One client doesn't affect others
- ✅ Can customize per client
- ✅ Easy to scale individual clients

**Cons:**
- ❌ More expensive ($6 per client)
- ❌ More servers to manage
- ❌ Overkill for small clients

**Best for:**
- Enterprise clients (willing to pay more)
- Clients with very different needs
- SLA requirements (99.9% uptime per client)
- Regulatory/compliance needs (data isolation)

**Cost:**
- 5 clients = $30/month (5 × $6)
- 10 clients = $60/month (10 × $6)

---

### Option 3: Hybrid Approach (Recommended for Growth)

**How it works:**
```
┌─────────────────────────┐  ┌─────────────────┐
│ Shared Server (4GB)     │  │ VIP Client      │
│ ┌─────────────────────┐ │  │ Dedicated (2GB) │
│ │ Small Client 1      │ │  └─────────────────┘
│ │ Small Client 2      │ │
│ │ Small Client 3      │ │  ┌─────────────────┐
│ │ Small Client 4      │ │  │ VIP Client 2    │
│ └─────────────────────┘ │  │ Dedicated (2GB) │
└─────────────────────────┘  └─────────────────┘
```

**Pricing Tiers:**
- **Basic Plan** ($50-100/month): Shared server, up to 50k products
- **Pro Plan** ($200-500/month): Shared server, up to 200k products
- **Enterprise Plan** ($1000+/month): Dedicated server, unlimited products

**Pros:**
- ✅ Cost-effective for small clients
- ✅ Premium offering for big clients
- ✅ Flexible and scalable

**Cons:**
- ⚠️ More complex to manage
- ⚠️ Need client management system

**Best for:**
- SaaS with multiple pricing tiers
- Mix of small and large clients
- Growing businesses

---

### Option 4: Use Typesense Cloud (Managed)

**How it works:**
- Let Typesense handle all infrastructure
- Auto-scaling
- Pay per usage

**Pros:**
- ✅ Zero server management
- ✅ Auto-scaling
- ✅ High availability built-in
- ✅ Focus on your app, not infrastructure

**Cons:**
- ❌ More expensive (~$22/month minimum per cluster)
- ❌ Less control

**Cost:**
- Shared cluster: $22/month (all clients)
- Per-client clusters: $22/month each

**Best for:**
- High-growth startups
- Don't want to manage infrastructure
- Need 99.9%+ uptime guarantees
- Willing to pay for convenience

---

## When to Scale Up?

### Monitor These Metrics

**1. Memory Usage**
```bash
# SSH into droplet
free -h

# If "used" > 80% → Time to upgrade
```

**2. Search Latency**
```bash
# In your app logs, track:
# - Average search time
# - 95th percentile search time

# If p95 > 500ms → Time to upgrade
```

**3. CPU Usage**
```bash
# Check CPU
htop

# If CPU > 80% consistently → Time to upgrade
```

### Scaling Triggers

| Metric | Current OK | Warning | Upgrade Now |
|--------|-----------|---------|-------------|
| RAM Usage | < 70% | 70-85% | > 85% |
| Search Latency (p95) | < 300ms | 300-500ms | > 500ms |
| CPU Usage | < 60% | 60-80% | > 80% |
| Total Products | < 100k | 100-200k | > 200k |

---

## Scaling Roadmap Examples

### Scenario 1: Bootstrapped SaaS (Cost-Conscious)

**Phase 1: 0-5 clients**
- **Setup**: 1 × 1GB droplet ($6/month)
- **Architecture**: Shared collections
- **Capacity**: Up to 150k products total

**Phase 2: 5-15 clients**
- **Setup**: Upgrade to 2GB droplet ($12/month)
- **Architecture**: Still shared collections
- **Capacity**: Up to 300k products total

**Phase 3: 15-30 clients**
- **Setup**: Upgrade to 4GB droplet ($24/month)
- **Architecture**: Shared + 1-2 dedicated for VIP clients
- **Capacity**: Up to 600k products shared + unlimited for VIPs

**Phase 4: 30+ clients**
- **Setup**: Multiple servers or migrate to Typesense Cloud
- **Architecture**: Hybrid approach
- **Cost**: $50-200/month depending on client mix

---

### Scenario 2: Funded Startup (Growth-Focused)

**Phase 1: MVP (1-10 clients)**
- **Setup**: Typesense Cloud shared cluster ($22/month)
- **Why**: Focus on product, not infrastructure

**Phase 2: Product-Market Fit (10-50 clients)**
- **Setup**: Typesense Cloud auto-scaling
- **Cost**: $22-100/month
- **Why**: Can handle growth without intervention

**Phase 3: Scale (50+ clients)**
- **Setup**: Move to self-hosted Kubernetes cluster
- **Cost**: $200-500/month
- **Why**: Cost optimization at scale

---

### Scenario 3: Enterprise/Agency (Per-Client Pricing)

**Setup**: Dedicated droplet per enterprise client
- **Small clients** (< 50k products): 1GB droplet ($6/month) → Charge $99-199/month
- **Medium clients** (50-200k products): 2GB droplet ($12/month) → Charge $299-499/month
- **Large clients** (200k+ products): 4GB+ droplet ($24+/month) → Charge $999+/month

**Margins**: 10-50x markup depending on value-add

---

## Migration Strategies

### Upgrading to Larger Droplet (Zero Downtime)

1. **Create snapshot of current droplet**
   ```bash
   # In DigitalOcean dashboard:
   Droplet → Snapshots → Take Snapshot
   ```

2. **Create new larger droplet from snapshot**
   ```bash
   # Create → Droplets → Choose snapshot
   # Select 2GB/4GB/8GB plan
   ```

3. **Update DNS/IP in your app**
   ```bash
   # Update .env
   TYPESENSE_HOST=NEW_DROPLET_IP
   ```

4. **Test new server**
   ```bash
   curl http://NEW_DROPLET_IP:8108/health
   ```

5. **Switch traffic, delete old droplet**

**Downtime**: < 1 minute (just DNS update)

---

### Adding New Dedicated Server for VIP Client

1. **Create new droplet** (same as setup guide)

2. **Install Typesense** (same as setup guide)

3. **Index client's data**
   ```bash
   # Update .env temporarily for this client
   TYPESENSE_HOST=VIP_CLIENT_DROPLET_IP

   # Run indexer with client's data
   python src/indexer_neon.py --client vip_client_id
   ```

4. **Route client's requests to dedicated server**
   ```python
   # In your backend
   def get_typesense_client(client_id):
       if client_id == "vip_client_123":
           return TypesenseClient({
               'nodes': [{'host': 'vip.droplet.ip', ...}]
           })
       else:
           return TypesenseClient({
               'nodes': [{'host': 'shared.droplet.ip', ...}]
           })
   ```

---

## Cost Comparison: Self-Hosted vs Cloud

### 5 Clients Scenario

| Option | Setup | Monthly Cost | Annual Cost |
|--------|-------|--------------|-------------|
| **Single 2GB Droplet** | Shared | $12 | $144 |
| **5 × 1GB Droplets** | Dedicated each | $30 | $360 |
| **Typesense Cloud Shared** | Managed | $22 | $264 |
| **5 × Typesense Cloud** | Managed each | $110 | $1,320 |

### 20 Clients Scenario

| Option | Setup | Monthly Cost | Annual Cost |
|--------|-------|--------------|-------------|
| **Single 8GB Droplet** | Shared | $48 | $576 |
| **Hybrid (4GB + 2 VIPs)** | Mixed | $60 | $720 |
| **20 × 1GB Droplets** | Dedicated each | $120 | $1,440 |
| **Typesense Cloud** | Managed | $100-200 | $1,200-2,400 |

---

## Multi-Tenant Code Implementation

### Collection Naming Strategy

```python
# In your backend
def get_collection_name(client_id):
    """Generate collection name per client."""
    return f"products_{client_id}"

# Examples:
# client_1 → "products_client_1"
# client_2 → "products_client_2"
```

### Dynamic Typesense Client

```python
# config.py
TYPESENSE_SERVERS = {
    "shared": {
        "host": "shared.droplet.ip",
        "port": 8108,
        "protocol": "http",
        "api_key": "shared_api_key"
    },
    "vip_client_123": {
        "host": "vip1.droplet.ip",
        "port": 8108,
        "protocol": "http",
        "api_key": "vip_api_key"
    }
}

# search.py
def get_typesense_client(client_id):
    """Get appropriate Typesense client for this customer."""
    if client_id in TYPESENSE_SERVERS:
        config = TYPESENSE_SERVERS[client_id]
    else:
        config = TYPESENSE_SERVERS["shared"]

    return typesense.Client({
        'nodes': [{
            'host': config['host'],
            'port': config['port'],
            'protocol': config['protocol']
        }],
        'api_key': config['api_key'],
        'connection_timeout_seconds': 2
    })

# Usage
client = get_typesense_client(request.client_id)
results = client.collections[collection_name].documents.search(params)
```

### API Endpoint with Multi-Tenancy

```python
@app.route("/api/search", methods=["POST"])
def search():
    # Get client ID from auth token/header
    client_id = get_client_id_from_request(request)

    # Get appropriate Typesense instance
    ts_client = get_typesense_client(client_id)

    # Get client's collection
    collection_name = f"products_{client_id}"

    # Execute search
    results = ts_client.collections[collection_name].documents.search({
        "q": query,
        # ... other params
    })

    return jsonify(results)
```

---

## Monitoring & Alerts

### Set Up Monitoring

**DigitalOcean Built-in Monitoring:**
1. Droplet → Graphs
2. Monitor: CPU, RAM, Disk, Bandwidth
3. Set up alerts (email/SMS)

**Custom Monitoring Script:**
```python
# monitor.py
import psutil
import requests

def check_health():
    # Check memory
    mem = psutil.virtual_memory()
    if mem.percent > 85:
        send_alert(f"Memory usage high: {mem.percent}%")

    # Check Typesense health
    try:
        response = requests.get("http://localhost:8108/health")
        if response.status_code != 200:
            send_alert("Typesense health check failed")
    except:
        send_alert("Typesense is down")

def send_alert(message):
    # Send email, Slack, SMS, etc.
    print(f"ALERT: {message}")

# Run every 5 minutes via cron
if __name__ == "__main__":
    check_health()
```

**Cron job:**
```bash
# Add to crontab
*/5 * * * * /usr/bin/python3 /root/monitor.py
```

---

## Quick Decision Matrix

**Choose based on your situation:**

| Your Situation | Recommended Option | Monthly Cost |
|----------------|-------------------|--------------|
| Just starting, 1-3 clients | Single 1GB droplet | $6 |
| Growing, 5-10 clients | Single 2GB droplet | $12 |
| 10-20 mixed clients | 4GB droplet + dedicated for VIPs | $24-60 |
| 20+ clients | Multiple droplets or Typesense Cloud | $50-200+ |
| High-growth startup | Typesense Cloud (managed) | $22-200+ |
| Enterprise SaaS | Dedicated per client | $120+ |

---

## TL;DR

**Can 1GB DigitalOcean handle multiple clients?**
- ✅ **2-5 clients** (~100-150k products total): YES
- ⚠️ **6-10 clients** (~200k products): Upgrade to 2GB ($12/month)
- ❌ **10+ clients** (300k+ products): Upgrade to 4GB+ or split servers

**Best approach as you grow:**
1. **Start**: 1GB shared ($6/month) - handles 5 clients
2. **Growth**: 2-4GB shared ($12-24/month) - handles 10-20 clients
3. **Scale**: Hybrid (shared + dedicated VIPs) - $50-100/month
4. **Enterprise**: Dedicated per client or Typesense Cloud

**Bottom line**: Start with 1GB, upgrade as needed. You'll know when it's time!
