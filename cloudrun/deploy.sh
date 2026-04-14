#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# ICAR Vision Backend — Cloud Run Deployment
# ============================================================
# Deploys to Cloud Run (serverless) in us-central1.
# Run this script from the PROJECT ROOT (parent of cloudrun/).
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - A GCP project with billing enabled
#
# Usage:
#   export GOOGLE_CLOUD_PROJECT=your-project-id
#   cd /path/to/project-root
#   ./cloudrun/deploy.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load env from cloudrun/.env if it exists
if [[ -f "${SCRIPT_DIR}/.env" ]]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT env var or add it to cloudrun/.env}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="icar-vision-backend"
SA_NAME="${SERVICE_NAME}"
SERVICE_ACCOUNT="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Deploying ${SERVICE_NAME} to Cloud Run"
echo "    Project:  ${PROJECT_ID}"
echo "    Region:   ${REGION}"
echo "    Source:   ${PROJECT_ROOT}"
echo ""

# 1. Enable required APIs
echo "==> Enabling APIs..."
gcloud services enable \
    aiplatform.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    --project="${PROJECT_ID}" --quiet

# 2. Create service account (idempotent)
echo "==> Creating service account ${SA_NAME}..."
gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="ICAR Vision Backend" \
    --project="${PROJECT_ID}" 2>/dev/null || true

# 3. Grant Vertex AI access to the service account
echo "==> Granting roles/aiplatform.user to ${SERVICE_ACCOUNT}..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --quiet

# 3b. Create conversation recording bucket and grant write access
CONV_BUCKET="${GCS_CONVERSATION_BUCKET:-kisan-mitra-conversations}"
echo "==> Creating GCS bucket gs://${CONV_BUCKET} for conversation recordings..."
gcloud storage buckets create "gs://${CONV_BUCKET}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --uniform-bucket-level-access 2>/dev/null || true

echo "==> Granting roles/storage.objectCreator to ${SERVICE_ACCOUNT} on gs://${CONV_BUCKET}..."
gcloud storage buckets add-iam-policy-binding "gs://${CONV_BUCKET}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectCreator" \
    --quiet 2>/dev/null || true

echo "==> Granting roles/storage.objectViewer to ${SERVICE_ACCOUNT} on gs://${CONV_BUCKET}..."
gcloud storage buckets add-iam-policy-binding "gs://${CONV_BUCKET}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectViewer" \
    --quiet 2>/dev/null || true

# 4. Deploy to Cloud Run (from project root where Dockerfile lives)
echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --source "${PROJECT_ROOT}" \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --service-account "${SERVICE_ACCOUNT}" \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},CROP_DIR=./crop,DISEASE_DIR=./diseases,GCS_CONVERSATION_BUCKET=${CONV_BUCKET},RECORD_AUDIO=true" \
    --session-affinity \
    --timeout 600 \
    --min-instances 1 \
    --max-instances 10 \
    --port 8080 \
    --allow-unauthenticated \
    --quiet

# 5. Print the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format='value(status.url)')

echo ""
echo "============================================================"
echo "Cloud Run deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo "WebSocket:   ${SERVICE_URL/https/wss}/ws/{user_id}/{session_id}"
echo "Health:      ${SERVICE_URL}/health"
echo "============================================================"
