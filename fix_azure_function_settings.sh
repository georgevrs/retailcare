#!/bin/bash
# Fix Azure Function App settings for Python v2 function discovery
# Run this to set all required settings at once

set -e

# CHANGE THESE TO YOUR VALUES
FUNCTION_APP_NAME="your-function-app-name"
RESOURCE_GROUP="your-resource-group"

echo "=========================================="
echo "Azure Functions Python v2 Settings Fix"
echo "=========================================="
echo ""
echo "Function App: $FUNCTION_APP_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# Check if logged in
echo "Checking Azure CLI login..."
az account show > /dev/null 2>&1 || {
    echo "ERROR: Not logged in to Azure CLI. Run 'az login' first."
    exit 1
}

echo "✅ Azure CLI authenticated"
echo ""

# Set all required settings
echo "Setting required app settings..."
az functionapp config appsettings set \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    "FUNCTIONS_WORKER_RUNTIME=python" \
    "AzureWebJobsFeatureFlags=EnableWorkerIndexing" \
  --output table

echo ""
echo "✅ Settings updated"
echo ""

# Restart the function app
echo "Restarting Function App..."
az functionapp restart \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RESOURCE_GROUP"

echo ""
echo "✅ Function App restarted"
echo ""
echo "=========================================="
echo "Wait 30-60 seconds, then check logs at:"
echo "https://portal.azure.com → Function App → Log stream"
echo ""
echo "You should see:"
echo "  'Reading functions metadata (Worker)'"
echo "  'N functions found (Worker)'"
echo "=========================================="
