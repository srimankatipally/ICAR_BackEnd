# Cloud Run Deployment

Deploys Kisan Mitra to **Google Cloud Run** (serverless) in **us-central1**.

Cloud Run automatically scales based on traffic (including scale-to-zero when idle). This is the recommended deployment for the Gemini Live Agent Challenge submission.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- A GCP project ID

## Quick Deploy (One-Click)

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

This uses `app.json` to configure the Cloud Run service automatically.

## Environment Setup

```bash
cp cloudrun/.env.example cloudrun/.env
# Edit cloudrun/.env with your GCP project ID
```

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID | (required) |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI / Cloud Run region | `us-central1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI backend | `TRUE` |
| `DEMO_AGENT_MODEL` | Gemini Live model | `gemini-live-2.5-flash-native-audio` |
| `CROP_DIR` | Path to crop knowledge base | `./crop` |
| `DISEASE_DIR` | Path to disease knowledge base | `./diseases` |

## Automated Deployment

Run from the **project root**:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
./cloudrun/deploy.sh
```

The script automatically:
1. Enables required APIs (Vertex AI, Cloud Run, Cloud Build)
2. Creates a service account with `roles/aiplatform.user`
3. Builds and deploys the container to Cloud Run
4. Prints the service URL

## Manual Deployment

```bash
gcloud run deploy icar-vision-backend \
  --source . \
  --region us-central1 \
  --project $GOOGLE_CLOUD_PROJECT \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT" \
  --allow-unauthenticated
```

## Vertex AI Permissions

The deploy script creates a dedicated service account and grants it `roles/aiplatform.user`. If deploying manually, ensure your Cloud Run service account has this role:

```bash
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
  --member="serviceAccount:YOUR_SA@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

## Service Details

| Property | Value |
|----------|-------|
| Region | us-central1 |
| Port | 8080 |
| Min instances | 1 |
| Max instances | 10 |
| Timeout | 600s |
| Session affinity | Enabled |
