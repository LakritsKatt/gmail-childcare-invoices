#!/usr/bin/env bash
set -euo pipefail

############################################
# Config — edit once, reuse forever, change to fit your deployment
############################################
PROJECT_ID="nursery-fee-app"
REGION="europe-west2"
REPO="nursery-invoice-repo"
IMAGE_NAME="nursery-invoice-app"
SERVICE_NAME="nursery-invoice-app"

# Tag strategy: use git SHA if available, else "latest"
TAG="${1:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"

# Full image URI in Artifact Registry
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:${TAG}"

# Env vars for your app (override via .env.prod if you prefer)
# GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-invoice-status}"
# SECRET_KEY="${SECRET_KEY:-change-me}"
# GOOGLE_CLIENT_SECRETS_FILE="/app/credentials.prod.json"

# Deploy flags
ALLOW_UNAUTH="${ALLOW_UNAUTH:-false}"   # set to "true" to make public
PLATFORM="managed"

############################################
# Pre-flight checks (helpful failures)
############################################
if [[ ! -f "credentials.prod.json" ]]; then
  echo "ERROR: credentials.prod.json not found in project root."
  echo "       This must be copied into the image by your Dockerfile."
  exit 1
fi

if ! gcloud config get-value project >/dev/null 2>&1; then
  echo "ERROR: gcloud not configured. Run: gcloud init"
  exit 1
fi

echo "Using config:"
echo "  Project:          ${PROJECT_ID}"
echo "  Region:           ${REGION}"
echo "  Repo:             ${REPO}"
echo "  Service:          ${SERVICE_NAME}"
echo "  Image URI:        ${IMAGE_URI}"
# echo "  GCS_BUCKET_NAME:  ${GCS_BUCKET_NAME}"
echo "  ALLOW_UNAUTH:     ${ALLOW_UNAUTH}"
echo

############################################
# Ensure gcloud is pointing to the right project/region
############################################
gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud config set run/region "${REGION}" >/dev/null

############################################
# Authenticate Docker for Artifact Registry
############################################
gcloud auth configure-docker "${REGION}-docker.pkg.dev" -q

############################################
# Build the image (Dockerfile in current dir)
############################################
echo "==> Building image: ${IMAGE_URI}"
docker build -t "${IMAGE_URI}" .

############################################
# Push to Artifact Registry
############################################
echo "==> Pushing image: ${IMAGE_URI}"
docker push "${IMAGE_URI}"

############################################
# Deploy to Cloud Run
############################################
DEPLOY_CMD=(
  gcloud run deploy "${SERVICE_NAME}"
  --image="${IMAGE_URI}"
  --platform="${PLATFORM}"
  --region="${REGION}"
)

if [[ "${ALLOW_UNAUTH}" == "true" ]]; then
  DEPLOY_CMD+=(--allow-unauthenticated)
fi

echo "==> Deploying to Cloud Run: ${SERVICE_NAME}"
"${DEPLOY_CMD[@]}"

############################################
# Done
############################################
echo
echo "✅ Deployed ${SERVICE_NAME} with image ${IMAGE_URI}"
echo "   Visit the Cloud Run console to see the URL and revisions."