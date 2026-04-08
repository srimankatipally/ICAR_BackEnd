# Compute Engine + HTTPS Load Balancer Deployment Guide

Complete guide for deploying Kisan Mitra on a persistent GCP Compute Engine VM in India (asia-south1) with an HTTPS Load Balancer for secure mic/camera access.

---

## Current Deployment Details

Reference for the live deployment (as of April 8, 2026):

| Resource | Value |
|----------|-------|
| **GCP Project ID** | `gen-lang-client-0028629353` |
| **GCP Project Name** | ICAR |
| **GCP Account** | `nimesh@nextcarbon.in` |
| **VM Instance** | `kisan-mitra-vm` |
| **VM Zone** | `asia-south1-b` (Mumbai, India) |
| **VM Machine Type** | `e2-medium` |
| **VM Static IP** | `34.14.169.254` |
| **VM OS** | Ubuntu 22.04 LTS |
| **Docker Image** | `kisan-mitra:latest` |
| **App Path on VM** | `/opt/kisan-mitra` |
| **Load Balancer IP** | `136.110.155.246` |
| **HTTPS URL** | `https://136.110.155.246` |
| **HTTP (redirects)** | `http://136.110.155.246` |
| **Direct VM (HTTP only)** | `http://34.14.169.254:8080` |
| **SSL Certificate** | Self-signed (CN=kisan-mitra, O=ICAR, C=IN, expires Apr 2027) |
| **Service Account** | `kisan-mitra-gce@gen-lang-client-0028629353.iam.gserviceaccount.com` |
| **Vertex AI Location** | `us-central1` (Gemini Live only available here) |
| **Model** | `gemini-live-2.5-flash-native-audio` |

### Quick Commands

```bash
# Set project
gcloud config set project gen-lang-client-0028629353

# SSH into VM
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=gen-lang-client-0028629353

# View logs
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=gen-lang-client-0028629353 \
    --command="sudo docker logs -f kisan-mitra"

# Restart container
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=gen-lang-client-0028629353 \
    --command="sudo docker restart kisan-mitra"

# Recreate container (after .env or code changes)
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=gen-lang-client-0028629353 \
    --command="cd /opt/kisan-mitra && sudo docker stop kisan-mitra && sudo docker rm kisan-mitra && sudo docker build -t kisan-mitra . && sudo docker run -d --name kisan-mitra --restart unless-stopped -p 8080:8080 --env-file .env kisan-mitra"

# Check backend health (load balancer)
gcloud compute backend-services get-health kisan-mitra-backend --global --project=gen-lang-client-0028629353

# Health check
curl --insecure https://136.110.155.246/health
```

### Cloud Run Deployment (Separate)

The Cloud Run deployment is independent and uses a different URL:

| Resource | Value |
|----------|-------|
| **Cloud Run URL** | `https://icar-vision-backend-ykitwyw32a-uc.a.run.app/` |
| **Region** | `us-central1` |

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [What Gets Created](#what-gets-created)
- [Prerequisites](#prerequisites)
- [Part 1: Compute Engine VM](#part-1-compute-engine-vm)
- [Part 2: HTTPS Load Balancer](#part-2-https-load-balancer)
- [Part 3: Verification](#part-3-verification)
- [Important Notes](#important-notes)
- [Monitoring and Logs](#monitoring-and-logs)
- [Updating the Application](#updating-the-application)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)
- [Cost Estimate](#cost-estimate)

---

## Architecture Overview

```
User (India)
    │
    │ HTTPS (port 443)
    ▼
┌──────────────────────────────────┐
│   GCP HTTPS Load Balancer        │
│   IP: 136.110.155.246            │
│   Self-signed SSL certificate    │
│   HTTP→HTTPS redirect            │
│   Session affinity (cookie)      │
│   WebSocket support              │
└──────────────┬───────────────────┘
               │ HTTP (port 8080)
               ▼
┌──────────────────────────────────┐
│   Compute Engine VM              │
│   Instance: kisan-mitra-vm       │
│   Zone: asia-south1-b (Mumbai)   │
│   Machine: e2-medium             │
│   Static IP: 34.14.169.254      │
│   OS: Ubuntu 22.04 + Docker      │
│                                  │
│   ┌──────────────────────────┐   │
│   │  Docker: kisan-mitra     │   │
│   │  FastAPI on port 8080    │   │
│   │  Gemini Live Agent       │   │
│   └──────────┬───────────────┘   │
│              │                   │
│   Service Account:               │
│   kisan-mitra-gce                │
│   Role: roles/aiplatform.user    │
│   Scope: cloud-platform          │
└──────────────┬───────────────────┘
               │ Vertex AI API
               ▼
┌──────────────────────────────────┐
│   Vertex AI (us-central1)        │
│   gemini-live-2.5-flash-         │
│   native-audio                   │
└──────────────────────────────────┘
```

**Why this setup:**
- **VM in India (asia-south1):** Low latency for Indian users (~10-30ms)
- **Vertex AI in us-central1:** Gemini Live model is only available in us-central1
- **HTTPS Load Balancer:** Browsers require HTTPS for mic/camera access (`getUserMedia`)
- **Always-on VM:** Unlike Cloud Run, never scales to zero

---

## What Gets Created

| Resource | Name | Purpose |
|----------|------|---------|
| Service Account | `kisan-mitra-gce` | Vertex AI access for the VM |
| Static IP (regional) | `kisan-mitra-vm-ip` | Permanent IP for the VM |
| Firewall Rule | `allow-kisan-mitra-http` | Open ports 80, 443, 8080 |
| VM Instance | `kisan-mitra-vm` | Application server |
| SSL Certificate | `kisan-mitra-ssl` | Self-signed cert for HTTPS |
| Instance Group | `kisan-mitra-ig` | Groups the VM for the LB |
| Health Check | `kisan-mitra-health` | Monitors /health endpoint |
| Backend Service | `kisan-mitra-backend` | LB backend config |
| URL Map | `kisan-mitra-lb` | Routes traffic to backend |
| HTTPS Proxy | `kisan-mitra-https-proxy` | Terminates SSL |
| HTTP Proxy | `kisan-mitra-http-proxy` | Redirects HTTP to HTTPS |
| Forwarding Rule (HTTPS) | `kisan-mitra-https-rule` | Public HTTPS entry point |
| Forwarding Rule (HTTP) | `kisan-mitra-http-rule` | HTTP redirect entry point |
| Static IP (global) | `kisan-mitra-lb-ip` | Permanent IP for the LB |
| URL Map (redirect) | `kisan-mitra-http-redirect` | HTTP→HTTPS redirect config |

---

## Prerequisites

1. **GCP account** with billing enabled
2. **`gcloud` CLI** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **OpenSSL** installed locally (for generating self-signed certificate)
4. Set your project ID as a variable (used throughout this guide):
   ```bash
   export PROJECT_ID=your-project-id
   ```

---

## Part 1: Compute Engine VM

### Step 1: Enable APIs

```bash
gcloud services enable compute.googleapis.com aiplatform.googleapis.com \
    --project=$PROJECT_ID --quiet
```

### Step 2: Create Service Account with Vertex AI Permissions

```bash
gcloud iam service-accounts create kisan-mitra-gce \
    --display-name="Kisan Mitra GCE" \
    --project=$PROJECT_ID

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:kisan-mitra-gce@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user" \
    --quiet
```

This grants `roles/aiplatform.user` which allows calling Vertex AI APIs including Gemini Live. The VM uses `cloud-platform` scope so credentials are fetched automatically from the GCE metadata server -- no JSON key files needed.

### Step 3: Reserve a Static IP

```bash
gcloud compute addresses create kisan-mitra-vm-ip \
    --region=asia-south1 \
    --project=$PROJECT_ID

# Get the IP address
VM_IP=$(gcloud compute addresses describe kisan-mitra-vm-ip \
    --region=asia-south1 --project=$PROJECT_ID --format='value(address)')
echo "VM Static IP: $VM_IP"
```

### Step 4: Create Firewall Rule

```bash
gcloud compute firewall-rules create allow-kisan-mitra-http \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:8080,tcp:80,tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=kisan-mitra \
    --description="Allow HTTP/HTTPS/8080 for Kisan Mitra" \
    --project=$PROJECT_ID
```

### Step 5: Create the VM

```bash
gcloud compute instances create kisan-mitra-vm \
    --zone=asia-south1-b \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-balanced \
    --service-account=kisan-mitra-gce@$PROJECT_ID.iam.gserviceaccount.com \
    --scopes=cloud-platform \
    --tags=kisan-mitra \
    --address=$VM_IP \
    --metadata=enable-oslogin=TRUE \
    --project=$PROJECT_ID
```

Wait ~20 seconds for the VM to boot.

### Step 6: Install Docker on the VM

```bash
gcloud compute ssh kisan-mitra-vm \
    --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        sudo apt-get update -qq
        sudo apt-get install -y -qq ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
            sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \\\$VERSION_CODENAME) stable\" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update -qq
        sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
        sudo usermod -aG docker \$USER
        docker --version
    "
```

### Step 7: Copy Project Files to the VM

**Option A -- Copy from local machine:**

```bash
gcloud compute scp --recurse --compress \
    /path/to/ICAR_F_B \
    kisan-mitra-vm:/tmp/kisan-mitra-upload \
    --zone=asia-south1-b --project=$PROJECT_ID

gcloud compute ssh kisan-mitra-vm \
    --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        sudo rm -rf /opt/kisan-mitra
        sudo mv /tmp/kisan-mitra-upload /opt/kisan-mitra
        sudo chown -R \$USER:\$USER /opt/kisan-mitra
    "
```

**Option B -- Clone from Git:**

```bash
gcloud compute ssh kisan-mitra-vm \
    --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        sudo git clone https://github.com/your-org/kisan-mitra.git /opt/kisan-mitra
        sudo chown -R \$USER:\$USER /opt/kisan-mitra
    "
```

### Step 8: Create the .env File

> **CRITICAL:** `GOOGLE_CLOUD_LOCATION` must be `us-central1` (not `asia-south1`).
> The Gemini Live model is only available in us-central1. The VM runs in India
> for low-latency serving, but Vertex AI API calls go to us-central1.

```bash
gcloud compute ssh kisan-mitra-vm \
    --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        cat > /opt/kisan-mitra/.env << 'EOF'
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1
DEMO_AGENT_MODEL=gemini-live-2.5-flash-native-audio
CROP_DIR=./crop
DISEASE_DIR=./diseases
EOF
    "
```

### Step 9: Build and Run the Docker Container

```bash
gcloud compute ssh kisan-mitra-vm \
    --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        cd /opt/kisan-mitra
        sudo docker build -t kisan-mitra .
        sudo docker run -d \
            --name kisan-mitra \
            --restart unless-stopped \
            -p 8080:8080 \
            --env-file .env \
            kisan-mitra
    "
```

### Step 10: Set Up systemd Service

This ensures the container auto-starts on VM reboot.

```bash
gcloud compute ssh kisan-mitra-vm \
    --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        sudo tee /etc/systemd/system/kisan-mitra.service > /dev/null << 'EOF'
[Unit]
Description=Kisan Mitra AI Assistant
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
ExecStartPre=-/usr/bin/docker stop kisan-mitra
ExecStartPre=-/usr/bin/docker rm kisan-mitra
ExecStart=/usr/bin/docker run --name kisan-mitra --restart unless-stopped -p 8080:8080 --env-file /opt/kisan-mitra/.env kisan-mitra
ExecStop=/usr/bin/docker stop kisan-mitra

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable kisan-mitra.service
    "
```

### Step 11: Verify the VM Deployment

```bash
# Health check via VM's direct IP
curl http://$VM_IP:8080/health
# Expected: {"status":"ok","app":"icar-vision"}

curl http://$VM_IP:8080/config
# Expected: {"model":"gemini-live-2.5-flash-native-audio","gcp_location":"us-central1","max_sessions":10}
```

At this point the application is running but only on HTTP. Browsers will block mic/camera on HTTP. Continue to Part 2 for HTTPS.

---

## Part 2: HTTPS Load Balancer

Browsers require HTTPS to allow `navigator.mediaDevices.getUserMedia()` (microphone and camera access). A GCP HTTPS Load Balancer terminates SSL and forwards traffic to the VM over HTTP.

### Step 1: Generate a Self-Signed SSL Certificate

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /tmp/kisan-mitra-key.pem \
    -out /tmp/kisan-mitra-cert.pem \
    -subj "/CN=kisan-mitra/O=ICAR/C=IN"
```

> If you have a domain name, use a Google-managed certificate instead
> (see [Alternative: Google-Managed Certificate](#alternative-google-managed-certificate)).

### Step 2: Upload the SSL Certificate

```bash
gcloud compute ssl-certificates create kisan-mitra-ssl \
    --certificate=/tmp/kisan-mitra-cert.pem \
    --private-key=/tmp/kisan-mitra-key.pem \
    --project=$PROJECT_ID
```

### Step 3: Create an Unmanaged Instance Group

```bash
gcloud compute instance-groups unmanaged create kisan-mitra-ig \
    --zone=asia-south1-b \
    --project=$PROJECT_ID

gcloud compute instance-groups unmanaged add-instances kisan-mitra-ig \
    --zone=asia-south1-b \
    --instances=kisan-mitra-vm \
    --project=$PROJECT_ID

gcloud compute instance-groups unmanaged set-named-ports kisan-mitra-ig \
    --zone=asia-south1-b \
    --named-ports=http:8080 \
    --project=$PROJECT_ID
```

### Step 4: Create a Health Check

```bash
gcloud compute health-checks create http kisan-mitra-health \
    --port=8080 \
    --request-path=/health \
    --check-interval=10s \
    --timeout=5s \
    --healthy-threshold=2 \
    --unhealthy-threshold=3 \
    --project=$PROJECT_ID
```

### Step 5: Create a Backend Service

```bash
gcloud compute backend-services create kisan-mitra-backend \
    --protocol=HTTP \
    --port-name=http \
    --health-checks=kisan-mitra-health \
    --timeout=600s \
    --connection-draining-timeout=300s \
    --session-affinity=GENERATED_COOKIE \
    --global \
    --project=$PROJECT_ID

gcloud compute backend-services add-backend kisan-mitra-backend \
    --instance-group=kisan-mitra-ig \
    --instance-group-zone=asia-south1-b \
    --balancing-mode=UTILIZATION \
    --max-utilization=0.8 \
    --global \
    --project=$PROJECT_ID
```

Key settings:
- `timeout=600s` -- long timeout for WebSocket connections
- `session-affinity=GENERATED_COOKIE` -- sticky sessions for WebSocket

### Step 6: Create URL Map and HTTPS Proxy

```bash
gcloud compute url-maps create kisan-mitra-lb \
    --default-service=kisan-mitra-backend \
    --global \
    --project=$PROJECT_ID

gcloud compute target-https-proxies create kisan-mitra-https-proxy \
    --url-map=kisan-mitra-lb \
    --ssl-certificates=kisan-mitra-ssl \
    --global \
    --project=$PROJECT_ID
```

### Step 7: Create the HTTPS Forwarding Rule

```bash
gcloud compute forwarding-rules create kisan-mitra-https-rule \
    --target-https-proxy=kisan-mitra-https-proxy \
    --ports=443 \
    --global \
    --project=$PROJECT_ID
```

Get the load balancer IP:

```bash
LB_IP=$(gcloud compute forwarding-rules describe kisan-mitra-https-rule \
    --global --project=$PROJECT_ID --format='value(IPAddress)')
echo "Load Balancer IP: $LB_IP"
```

### Step 8: Reserve the Load Balancer IP and Add HTTP Redirect

```bash
# Reserve the ephemeral IP so it becomes static
gcloud compute addresses create kisan-mitra-lb-ip \
    --addresses=$LB_IP \
    --global \
    --project=$PROJECT_ID

# Create HTTP-to-HTTPS redirect URL map
gcloud compute url-maps import kisan-mitra-http-redirect \
    --global --project=$PROJECT_ID --source=- << 'EOF'
name: kisan-mitra-http-redirect
defaultUrlRedirect:
  httpsRedirect: true
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
EOF

# Create HTTP proxy and forwarding rule
gcloud compute target-http-proxies create kisan-mitra-http-proxy \
    --url-map=kisan-mitra-http-redirect \
    --global \
    --project=$PROJECT_ID

gcloud compute forwarding-rules create kisan-mitra-http-rule \
    --target-http-proxy=kisan-mitra-http-proxy \
    --ports=80 \
    --address=kisan-mitra-lb-ip \
    --global \
    --project=$PROJECT_ID
```

### Step 9: Wait for Propagation

The load balancer takes 3-5 minutes to fully provision. Check with:

```bash
# Check backend health (should show HEALTHY)
gcloud compute backend-services get-health kisan-mitra-backend \
    --global --project=$PROJECT_ID

# Test HTTPS (--insecure because self-signed cert)
curl --insecure https://$LB_IP/health
```

---

## Part 3: Verification

### Final URLs

| URL | Purpose |
|-----|---------|
| `https://<LB_IP>` | Main application (HTTPS, mic/camera work) |
| `https://<LB_IP>/health` | Health check |
| `https://<LB_IP>/config` | Configuration info |
| `https://<LB_IP>/test` | Developer test console |
| `wss://<LB_IP>/ws/{user_id}/{session_id}` | WebSocket (voice/video) |
| `wss://<LB_IP>/ws/text/{user_id}/{session_id}` | WebSocket (text only) |
| `http://<VM_IP>:8080` | Direct VM access (HTTP only, no mic/camera) |

### Browser Access

1. Open `https://<LB_IP>` in Chrome
2. You will see a **"Your connection is not private"** warning (self-signed cert)
3. Click **Advanced** then **Proceed to \<IP\> (unsafe)**
4. The app loads with full mic/camera/WebSocket access

### Test Each Mode

- **Text Chat:** Type a message and verify you get a response
- **Voice Input:** Tap the mic button, speak, and verify audio response
- **Video Query:** Allow camera access, show something, and verify AI sees it

---

## Important Notes

### Gemini Live Model Region

The `GOOGLE_CLOUD_LOCATION` environment variable MUST be `us-central1`. The Gemini Live model (`gemini-live-2.5-flash-native-audio`) is only deployed in `us-central1`. Setting it to `asia-south1` causes this error:

```
google.genai.errors.APIError: 1008 None. Publisher Model
projects/.../locations/asia-south1/publishers/google/models/gemini-live-2.5-flash-n
```

The VM itself runs in `asia-south1` for low-latency web serving. Only the Vertex AI API calls go to `us-central1`.

### Self-Signed Certificate Warning

Since we use a self-signed certificate, browsers show a security warning on first visit. This is expected. Users need to click through it once. For production with no warning, either:
- Use a domain name with a Google-managed certificate
- Use Let's Encrypt with Nginx on the VM directly

### WebSocket Through the Load Balancer

GCP HTTPS Load Balancers natively support WebSocket. The `Connection: Upgrade` header passes through automatically. The 600s backend timeout ensures long-lived WebSocket sessions stay open.

---

## Monitoring and Logs

### Container Logs

```bash
# SSH into VM
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$PROJECT_ID

# Follow logs in real time
sudo docker logs -f kisan-mitra

# Last 100 lines
sudo docker logs --tail 100 kisan-mitra
```

### systemd Service Status

```bash
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$PROJECT_ID \
    --command="sudo systemctl status kisan-mitra.service"
```

### Load Balancer Backend Health

```bash
gcloud compute backend-services get-health kisan-mitra-backend \
    --global --project=$PROJECT_ID
```

### Quick Health Check

```bash
# Via Load Balancer (HTTPS)
curl --insecure https://<LB_IP>/health

# Via VM directly (HTTP)
curl http://<VM_IP>:8080/health
```

---

## Updating the Application

### Deploy a New Version

```bash
# Option A: Copy updated files from local
gcloud compute scp --recurse --compress \
    /path/to/ICAR_F_B \
    kisan-mitra-vm:/tmp/kisan-mitra-upload \
    --zone=asia-south1-b --project=$PROJECT_ID

gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        sudo rm -rf /opt/kisan-mitra
        sudo mv /tmp/kisan-mitra-upload /opt/kisan-mitra
        sudo chown -R \$USER:\$USER /opt/kisan-mitra
        cp /opt/kisan-mitra/.env.bak /opt/kisan-mitra/.env 2>/dev/null || true
        cd /opt/kisan-mitra
        sudo docker stop kisan-mitra && sudo docker rm kisan-mitra
        sudo docker build -t kisan-mitra .
        sudo docker run -d --name kisan-mitra --restart unless-stopped \
            -p 8080:8080 --env-file .env kisan-mitra
    "
```

```bash
# Option B: Pull from git
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        cd /opt/kisan-mitra && git pull origin main
        sudo docker stop kisan-mitra && sudo docker rm kisan-mitra
        sudo docker build -t kisan-mitra .
        sudo docker run -d --name kisan-mitra --restart unless-stopped \
            -p 8080:8080 --env-file .env kisan-mitra
    "
```

### Update Environment Variables

```bash
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$PROJECT_ID \
    --command="
        # Edit the .env file
        nano /opt/kisan-mitra/.env

        # Recreate the container (restart won't pick up .env changes)
        sudo docker stop kisan-mitra && sudo docker rm kisan-mitra
        sudo docker run -d --name kisan-mitra --restart unless-stopped \
            -p 8080:8080 --env-file /opt/kisan-mitra/.env kisan-mitra
    "
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Mic/camera blocked on HTTP | Browsers require HTTPS for getUserMedia | Use the HTTPS load balancer URL |
| `APIError: 1008 policy violation` | GOOGLE_CLOUD_LOCATION set to asia-south1 | Change to `us-central1` in .env, recreate container |
| WebSocket won't connect (red dot) | Backend service timeout too low, or container crashed | Check `docker logs`, verify backend health |
| LB returns 502 | Backend not healthy, container down | Run `docker ps`, check health check status |
| LB returns 0 (connection refused) | LB still provisioning | Wait 3-5 minutes after creation |
| Self-signed cert warning | Expected with self-signed certificates | Click Advanced > Proceed, or use a real domain |
| Container won't start after reboot | systemd service not enabled | Run `sudo systemctl enable kisan-mitra.service` |
| Docker permission denied | User not in docker group | Run `sudo usermod -aG docker $USER`, log out and back in |

---

## Cleanup

Remove all resources in reverse order:

```bash
# 1. Load Balancer resources
gcloud compute forwarding-rules delete kisan-mitra-http-rule \
    --global --project=$PROJECT_ID --quiet
gcloud compute forwarding-rules delete kisan-mitra-https-rule \
    --global --project=$PROJECT_ID --quiet
gcloud compute target-http-proxies delete kisan-mitra-http-proxy \
    --project=$PROJECT_ID --quiet
gcloud compute target-https-proxies delete kisan-mitra-https-proxy \
    --project=$PROJECT_ID --quiet
gcloud compute url-maps delete kisan-mitra-http-redirect \
    --global --project=$PROJECT_ID --quiet
gcloud compute url-maps delete kisan-mitra-lb \
    --global --project=$PROJECT_ID --quiet
gcloud compute backend-services delete kisan-mitra-backend \
    --global --project=$PROJECT_ID --quiet
gcloud compute health-checks delete kisan-mitra-health \
    --project=$PROJECT_ID --quiet
gcloud compute instance-groups unmanaged delete kisan-mitra-ig \
    --zone=asia-south1-b --project=$PROJECT_ID --quiet
gcloud compute ssl-certificates delete kisan-mitra-ssl \
    --project=$PROJECT_ID --quiet
gcloud compute addresses delete kisan-mitra-lb-ip \
    --global --project=$PROJECT_ID --quiet

# 2. VM resources
gcloud compute instances delete kisan-mitra-vm \
    --zone=asia-south1-b --project=$PROJECT_ID --quiet
gcloud compute addresses delete kisan-mitra-vm-ip \
    --region=asia-south1 --project=$PROJECT_ID --quiet
gcloud compute firewall-rules delete allow-kisan-mitra-http \
    --project=$PROJECT_ID --quiet

# 3. Service account
gcloud iam service-accounts delete \
    kisan-mitra-gce@$PROJECT_ID.iam.gserviceaccount.com \
    --project=$PROJECT_ID --quiet
```

---

## Cost Estimate

| Resource | Approximate Monthly Cost |
|----------|-------------------------|
| e2-medium VM (asia-south1) | ~$25 |
| 30GB pd-balanced disk | ~$5 |
| Static IP (VM) | ~$3 (free while attached to running VM) |
| HTTPS Load Balancer | ~$18 (forwarding rule) |
| Static IP (LB) | ~$3 (free while in use) |
| Outbound traffic (estimated) | ~$1-5 |
| **Total** | **~$50-55/month** |

Vertex AI (Gemini Live) usage is billed separately based on token consumption.

---

## Alternative: Google-Managed Certificate

If you have a domain name, replace the self-signed certificate steps with:

```bash
# Point your domain's DNS A record to the LB IP first, then:
gcloud compute ssl-certificates create kisan-mitra-ssl-managed \
    --domains=your-domain.com \
    --global \
    --project=$PROJECT_ID

# Use kisan-mitra-ssl-managed instead of kisan-mitra-ssl
# in the target-https-proxies create command
```

Google will automatically provision and renew the certificate. No browser warning.
