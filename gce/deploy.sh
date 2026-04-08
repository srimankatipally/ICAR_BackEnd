#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# ICAR Vision Backend — GCP Compute Engine Deployment
# ============================================================
# Deploys to a persistent Compute Engine VM in asia-south1
# (Mumbai, India) for low-latency access by Indian users.
#
# Run this script from the PROJECT ROOT (parent of gce/).
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - A GCP project with billing enabled
#   - Git repository URL (or local files to copy)
#
# Usage:
#   export GOOGLE_CLOUD_PROJECT=your-project-id
#   cd /path/to/project-root
#   ./gce/deploy.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load env from gce/.env if it exists
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT env var or add it to gce/.env}"
REGION="${GOOGLE_CLOUD_LOCATION:-asia-south1}"
ZONE="${GCE_ZONE:-${REGION}-b}"
INSTANCE_NAME="${GCE_INSTANCE_NAME:-kisan-mitra-vm}"
MACHINE_TYPE="${GCE_MACHINE_TYPE:-e2-medium}"
SA_NAME="kisan-mitra-gce"
SERVICE_ACCOUNT="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
STATIC_IP_NAME="${INSTANCE_NAME}-ip"
FIREWALL_RULE="allow-kisan-mitra-http"
GIT_REPO="${GIT_REPO_URL:-}"

echo "============================================================"
echo "  Kisan Mitra — Compute Engine Deployment"
echo "============================================================"
echo "  Project:       ${PROJECT_ID}"
echo "  Region/Zone:   ${REGION} / ${ZONE}"
echo "  Instance:      ${INSTANCE_NAME}"
echo "  Machine type:  ${MACHINE_TYPE}"
echo "============================================================"
echo ""

# -------------------------------------------------------
# 1. Enable required APIs
# -------------------------------------------------------
echo "==> [1/8] Enabling APIs..."
gcloud services enable \
    compute.googleapis.com \
    aiplatform.googleapis.com \
    --project="${PROJECT_ID}" --quiet

# -------------------------------------------------------
# 2. Create service account with Vertex AI permissions
# -------------------------------------------------------
echo "==> [2/8] Creating service account ${SA_NAME}..."
gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="Kisan Mitra GCE" \
    --project="${PROJECT_ID}" 2>/dev/null || true

echo "==> Granting roles/aiplatform.user..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --quiet

# -------------------------------------------------------
# 3. Reserve a static external IP
# -------------------------------------------------------
echo "==> [3/8] Reserving static IP ${STATIC_IP_NAME}..."
gcloud compute addresses create "${STATIC_IP_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" 2>/dev/null || true

STATIC_IP=$(gcloud compute addresses describe "${STATIC_IP_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format='value(address)')
echo "    Static IP: ${STATIC_IP}"

# -------------------------------------------------------
# 4. Create firewall rule for port 8080
# -------------------------------------------------------
echo "==> [4/8] Creating firewall rule ${FIREWALL_RULE}..."
gcloud compute firewall-rules create "${FIREWALL_RULE}" \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:8080,tcp:80,tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=kisan-mitra \
    --description="Allow HTTP/HTTPS/8080 for Kisan Mitra" \
    --project="${PROJECT_ID}" 2>/dev/null || true

# -------------------------------------------------------
# 5. Create the VM instance
# -------------------------------------------------------
echo "==> [5/8] Creating VM instance ${INSTANCE_NAME}..."
gcloud compute instances create "${INSTANCE_NAME}" \
    --zone="${ZONE}" \
    --machine-type="${MACHINE_TYPE}" \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-balanced \
    --service-account="${SERVICE_ACCOUNT}" \
    --scopes=cloud-platform \
    --tags=kisan-mitra \
    --address="${STATIC_IP}" \
    --metadata=enable-oslogin=TRUE \
    --project="${PROJECT_ID}" 2>/dev/null || {
        echo "    VM already exists or creation failed. Continuing..."
    }

# Wait for VM to be ready
echo "==> Waiting for VM to be reachable..."
sleep 15

# -------------------------------------------------------
# 6. Install Docker on the VM
# -------------------------------------------------------
echo "==> [6/8] Installing Docker on VM..."
gcloud compute ssh "${INSTANCE_NAME}" \
    --zone="${ZONE}" \
    --project="${PROJECT_ID}" \
    --command="
        if ! command -v docker &> /dev/null; then
            echo '==> Installing Docker...'
            sudo apt-get update -qq
            sudo apt-get install -y -qq ca-certificates curl gnupg
            sudo install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            sudo chmod a+r /etc/apt/keyrings/docker.gpg
            echo 'deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable' | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update -qq
            sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo usermod -aG docker \$USER
            echo '==> Docker installed successfully'
        else
            echo '==> Docker already installed'
        fi
    "

# -------------------------------------------------------
# 7. Deploy application on VM
# -------------------------------------------------------
echo "==> [7/8] Deploying application..."

if [[ -n "${GIT_REPO}" ]]; then
    echo "    Cloning from ${GIT_REPO}..."
    gcloud compute ssh "${INSTANCE_NAME}" \
        --zone="${ZONE}" \
        --project="${PROJECT_ID}" \
        --command="
            sudo rm -rf /opt/kisan-mitra
            sudo git clone ${GIT_REPO} /opt/kisan-mitra
            sudo chown -R \$USER:\$USER /opt/kisan-mitra
        "
else
    echo "    Copying project files from local..."
    gcloud compute scp --recurse \
        "${PROJECT_ROOT}" \
        "${INSTANCE_NAME}:/tmp/kisan-mitra-upload" \
        --zone="${ZONE}" \
        --project="${PROJECT_ID}"

    gcloud compute ssh "${INSTANCE_NAME}" \
        --zone="${ZONE}" \
        --project="${PROJECT_ID}" \
        --command="
            sudo rm -rf /opt/kisan-mitra
            sudo mv /tmp/kisan-mitra-upload /opt/kisan-mitra
            sudo chown -R \$USER:\$USER /opt/kisan-mitra
        "
fi

# Create .env on the VM
echo "    Writing .env file..."
gcloud compute ssh "${INSTANCE_NAME}" \
    --zone="${ZONE}" \
    --project="${PROJECT_ID}" \
    --command="
        cat > /opt/kisan-mitra/.env << 'ENVEOF'
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GOOGLE_CLOUD_LOCATION=us-central1
DEMO_AGENT_MODEL=gemini-live-2.5-flash-native-audio
CROP_DIR=./crop
DISEASE_DIR=./diseases
ENVEOF
    "

# Build and run Docker container
echo "    Building Docker image..."
gcloud compute ssh "${INSTANCE_NAME}" \
    --zone="${ZONE}" \
    --project="${PROJECT_ID}" \
    --command="
        cd /opt/kisan-mitra
        sudo docker stop kisan-mitra 2>/dev/null || true
        sudo docker rm kisan-mitra 2>/dev/null || true
        sudo docker build -t kisan-mitra .
        sudo docker run -d \
            --name kisan-mitra \
            --restart unless-stopped \
            -p 8080:8080 \
            --env-file .env \
            kisan-mitra
        echo '==> Container started'
    "

# -------------------------------------------------------
# 8. Set up systemd service for auto-restart
# -------------------------------------------------------
echo "==> [8/8] Setting up systemd service..."
gcloud compute ssh "${INSTANCE_NAME}" \
    --zone="${ZONE}" \
    --project="${PROJECT_ID}" \
    --command="
        sudo tee /etc/systemd/system/kisan-mitra.service > /dev/null << 'SVCEOF'
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
SVCEOF

        sudo systemctl daemon-reload
        sudo systemctl enable kisan-mitra.service
        echo '==> systemd service configured'
    "

# -------------------------------------------------------
# Done
# -------------------------------------------------------
echo ""
echo "============================================================"
echo "  Compute Engine deployment complete!"
echo ""
echo "  Instance:    ${INSTANCE_NAME}"
echo "  Zone:        ${ZONE}"
echo "  Static IP:   ${STATIC_IP}"
echo ""
echo "  Application: http://${STATIC_IP}:8080"
echo "  WebSocket:   ws://${STATIC_IP}:8080/ws/{user_id}/{session_id}"
echo "  Health:      http://${STATIC_IP}:8080/health"
echo ""
echo "  SSH into VM:"
echo "    gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE} --project=${PROJECT_ID}"
echo ""
echo "  View logs:"
echo "    gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE} --project=${PROJECT_ID} --command='sudo docker logs -f kisan-mitra'"
echo "============================================================"
