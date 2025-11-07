#!/bin/bash

# This script tells Vercel to skip backend builds when only frontend files changed
# Exit code 1 = build, Exit code 0 = skip build

echo "🔍 Checking if backend files changed..."

# Check if this is the first deployment
if [ "$VERCEL_GIT_PREVIOUS_SHA" = "" ]; then
  echo "✅ First deployment, building backend"
  exit 1
fi

# Get list of changed files
CHANGED_FILES=$(git diff --name-only $VERCEL_GIT_PREVIOUS_SHA $VERCEL_GIT_COMMIT_SHA)

echo "Changed files:"
echo "$CHANGED_FILES"

# Check if any backend files changed
if echo "$CHANGED_FILES" | grep -qE "^(api/|src/|vercel.json|runtime.txt|requirements.txt|middleware/)"; then
  echo "✅ Backend files changed, building"
  exit 1
fi

# Check if only frontend files changed
if echo "$CHANGED_FILES" | grep -q "^frontend-next/"; then
  echo "⏭️  Only frontend files changed, skipping backend build"
  exit 0
fi

# If docs or other files changed, still build
echo "✅ Other files changed, building to be safe"
exit 1
