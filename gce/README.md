# Compute Engine Deployment (India Region)

Deploys Kisan Mitra to a **persistent GCP Compute Engine VM** in **asia-south1 (Mumbai, India)** for always-on availability and low latency for Indian users.

Unlike Cloud Run (which can scale to zero), a Compute Engine VM runs 24/7 -- your application is always ready to serve requests.

## Cloud Run vs Compute Engine

| | Cloud Run | Compute Engine |
|---|---|---|
| **Type** | Serverless container | Persistent VM |
| **Region** | us-central1 | asia-south1 (Mumbai) |
| **Always on** | Scales to zero when idle | Always running |
| **Latency (India)** | ~150-200ms (US region) | ~10-30ms (Mumbai) |
| **Auto-scaling** | Automatic (0 to N) | Manual (single VM) |
| **Cost model** | Pay per request | Pay per hour (~$25/mo for e2-medium) |
| **Setup complexity** | Low (one command) | Medium (VM + Docker + firewall) |
| **Best for** | Development, demos, variable traffic | Production in India, consistent traffic |

## Prerequisites

1. **GCP account** with billing enabled
2. **`gcloud` CLI** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project your-project-id
   ```
3. **Vertex AI API** enabled on your project

## Environment Setup

```bash
cp gce/.env.example gce/.env
# Edit gce/.env with your GCP project ID
```

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID | (required) |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region (must be us-central1) | `us-central1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI backend | `TRUE` |
| `DEMO_AGENT_MODEL` | Gemini Live model | `gemini-live-2.5-flash-native-audio` |
| `GCE_ZONE` | Compute Engine zone | `asia-south1-b` |
| `GCE_INSTANCE_NAME` | VM instance name | `kisan-mitra-vm` |
| `GCE_MACHINE_TYPE` | VM machine type | `e2-medium` |
| `GIT_REPO_URL` | Git repo to clone (optional) | (empty = copy local files) |

## Automated Deployment

Run from the **project root**:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
./gce/deploy.sh
```

The script automatically:
1. Enables Compute Engine and Vertex AI APIs
2. Creates a service account with `roles/aiplatform.user`
3. Reserves a static external IP in asia-south1
4. Creates firewall rules for ports 80, 443, and 8080
5. Creates an `e2-medium` Ubuntu 22.04 VM with the service account attached
6. Installs Docker on the VM
7. Copies project files (or clones from git) and builds the Docker image
8. Sets up a systemd service for auto-restart on boot

## Manual Step-by-Step Deployment

### 1. Enable APIs

```bash
gcloud services enable compute.googleapis.com aiplatform.googleapis.com \
    --project=$GOOGLE_CLOUD_PROJECT
```

### 2. Create Service Account with Vertex AI Permissions

```bash
# Create the service account
gcloud iam service-accounts create kisan-mitra-gce \
    --display-name="Kisan Mitra GCE" \
    --project=$GOOGLE_CLOUD_PROJECT

# Grant Vertex AI access
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:kisan-mitra-gce@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

The `roles/aiplatform.user` role allows the VM to call Vertex AI APIs (including Gemini Live). The service account is attached to the VM with `cloud-platform` scope, so no JSON key file is needed.

### 3. Reserve a Static IP

```bash
gcloud compute addresses create kisan-mitra-vm-ip \
    --region=asia-south1 \
    --project=$GOOGLE_CLOUD_PROJECT

# Note the IP address
gcloud compute addresses describe kisan-mitra-vm-ip \
    --region=asia-south1 --format='value(address)'
```

### 4. Create Firewall Rule

```bash
gcloud compute firewall-rules create allow-kisan-mitra-http \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:8080,tcp:80,tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=kisan-mitra \
    --project=$GOOGLE_CLOUD_PROJECT
```

### 5. Create the VM

```bash
gcloud compute instances create kisan-mitra-vm \
    --zone=asia-south1-b \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-balanced \
    --service-account=kisan-mitra-gce@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com \
    --scopes=cloud-platform \
    --tags=kisan-mitra \
    --address=STATIC_IP_HERE \
    --project=$GOOGLE_CLOUD_PROJECT
```

### 6. SSH into the VM and Install Docker

```bash
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$GOOGLE_CLOUD_PROJECT
```

Inside the VM:

```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER

# Log out and back in for group change to take effect
exit
```

### 7. Deploy the Application

SSH back in, then:

```bash
# Clone or copy project files to /opt/kisan-mitra
cd /opt/kisan-mitra

# Create .env file
cat > .env << 'EOF'
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
DEMO_AGENT_MODEL=gemini-live-2.5-flash-native-audio
CROP_DIR=./crop
DISEASE_DIR=./diseases
EOF

# Build and run
sudo docker build -t kisan-mitra .
sudo docker run -d \
    --name kisan-mitra \
    --restart unless-stopped \
    -p 8080:8080 \
    --env-file .env \
    kisan-mitra
```

### 8. Set Up systemd Service

Create `/etc/systemd/system/kisan-mitra.service`:

```ini
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
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kisan-mitra.service
sudo systemctl start kisan-mitra.service
```

## Vertex AI Permissions (Detailed)

The Compute Engine VM authenticates to Vertex AI through its **attached service account** -- no JSON key files needed.

| Component | Value |
|-----------|-------|
| Service account | `kisan-mitra-gce@PROJECT_ID.iam.gserviceaccount.com` |
| IAM role | `roles/aiplatform.user` |
| VM scope | `cloud-platform` |
| Auth method | Automatic (metadata server) |

The `cloud-platform` scope on the VM allows the Google client libraries to automatically fetch credentials from the GCE metadata server. The `roles/aiplatform.user` IAM role grants permission to call Vertex AI prediction endpoints, including Gemini Live.

## Optional: HTTPS with Nginx + Let's Encrypt

For production use with a custom domain:

```bash
# Install Nginx and Certbot on the VM
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Configure Nginx as a reverse proxy
sudo tee /etc/nginx/sites-available/kisan-mitra << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/kisan-mitra /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

After this, your app is accessible at `https://your-domain.com` with WebSocket support at `wss://your-domain.com/ws/{user_id}/{session_id}`.

## Monitoring and Logs

### View container logs

```bash
# SSH into VM
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$GOOGLE_CLOUD_PROJECT

# Follow logs
sudo docker logs -f kisan-mitra

# Last 100 lines
sudo docker logs --tail 100 kisan-mitra
```

### Check service status

```bash
sudo systemctl status kisan-mitra.service
sudo journalctl -u kisan-mitra.service -f
```

### Check container health

```bash
curl http://localhost:8080/health
```

### Restart the application

```bash
sudo docker restart kisan-mitra
# or
sudo systemctl restart kisan-mitra.service
```

## Updating the Application

To deploy a new version:

```bash
# SSH into VM
gcloud compute ssh kisan-mitra-vm --zone=asia-south1-b --project=$GOOGLE_CLOUD_PROJECT

cd /opt/kisan-mitra

# Pull latest code (if using git)
git pull origin main

# Rebuild and restart
sudo docker stop kisan-mitra
sudo docker rm kisan-mitra
sudo docker build -t kisan-mitra .
sudo docker run -d \
    --name kisan-mitra \
    --restart unless-stopped \
    -p 8080:8080 \
    --env-file .env \
    kisan-mitra
```

## Cleanup

To remove all resources created by this deployment:

```bash
# Delete the VM
gcloud compute instances delete kisan-mitra-vm \
    --zone=asia-south1-b --project=$GOOGLE_CLOUD_PROJECT --quiet

# Release the static IP
gcloud compute addresses delete kisan-mitra-vm-ip \
    --region=asia-south1 --project=$GOOGLE_CLOUD_PROJECT --quiet

# Delete the firewall rule
gcloud compute firewall-rules delete allow-kisan-mitra-http \
    --project=$GOOGLE_CLOUD_PROJECT --quiet

# Delete the service account
gcloud iam service-accounts delete \
    kisan-mitra-gce@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com \
    --project=$GOOGLE_CLOUD_PROJECT --quiet
```
