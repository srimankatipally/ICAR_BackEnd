#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# ICAR Vision Backend — Cloud Run Deployment
# ============================================================
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - A GCP project with billing enabled
#   - Vertex AI API enabled:
#       gcloud services enable aiplatform.googleapis.com
# ============================================================

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT env var}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="icar-vision-backend"
SA_NAME="${SERVICE_NAME}"
SERVICE_ACCOUNT="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Deploying ${SERVICE_NAME} to ${REGION} in project ${PROJECT_ID}"

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

# 4. Deploy to Cloud Run
echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --service-account "${SERVICE_ACCOUNT}" \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},CROP_DIR=./crop,DISEASE_DIR=./diseases" \
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
echo "Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo "WebSocket:   ${SERVICE_URL/https/wss}/ws/{user_id}/{session_id}"
echo "Health:      ${SERVICE_URL}/health"
echo "============================================================"
