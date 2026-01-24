# Fix Azure Function App Settings for Cognitive Services
# This script updates the environment variables in Azure to match local.settings.json

$FunctionAppName = "retailcare-callcenter-fn-g6e9e6a2grgberd2"
$ResourceGroup = "mlfunq7-a03b2-rg-francecentral"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Function App Settings Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is available
$azAvailable = Get-Command az -ErrorAction SilentlyContinue
if (-not $azAvailable) {
    Write-Host "❌ Azure CLI (az) is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "MANUAL FIX REQUIRED:" -ForegroundColor Yellow
    Write-Host "1. Go to Azure Portal" -ForegroundColor White
    Write-Host "2. Navigate to Function App: $FunctionAppName" -ForegroundColor White
    Write-Host "3. Go to Settings > Environment variables" -ForegroundColor White
    Write-Host "4. Update or add these settings:" -ForegroundColor White
    Write-Host ""
    Write-Host "   AZURE_OPENAI_ENDPOINT = https://georg-misszhma-centralus.cognitiveservices.azure.com/" -ForegroundColor Green
    Write-Host "   SPEECH_REGION = francecentral" -ForegroundColor Green
    Write-Host ""
    Write-Host "5. Click 'Apply' and restart the function app" -ForegroundColor White
    Write-Host ""
    Write-Host "Alternative: Use Azure Portal Cloud Shell or install Azure CLI" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Azure CLI found" -ForegroundColor Green
Write-Host ""

# Check current settings
Write-Host "Checking current Azure Function App settings..." -ForegroundColor Yellow
Write-Host ""

try {
    $currentSettings = az functionapp config appsettings list `
        --name $FunctionAppName `
        --resource-group $ResourceGroup `
        --query "[?name=='AZURE_OPENAI_ENDPOINT' || name=='SPEECH_REGION'].{name:name, value:value}" `
        --output json | ConvertFrom-Json
    
    Write-Host "Current Settings:" -ForegroundColor Cyan
    foreach ($setting in $currentSettings) {
        Write-Host "  $($setting.name) = $($setting.value)" -ForegroundColor White
    }
    Write-Host ""
    
    # Expected values
    $expectedEndpoint = "https://georg-misszhma-centralus.cognitiveservices.azure.com/"
    $expectedRegion = "francecentral"
    
    $needsUpdate = $false
    
    $currentEndpoint = ($currentSettings | Where-Object { $_.name -eq "AZURE_OPENAI_ENDPOINT" }).value
    $currentRegion = ($currentSettings | Where-Object { $_.name -eq "SPEECH_REGION" }).value
    
    if ($currentEndpoint -ne $expectedEndpoint) {
        Write-Host "⚠️  AZURE_OPENAI_ENDPOINT is wrong!" -ForegroundColor Red
        Write-Host "   Current:  $currentEndpoint" -ForegroundColor Red
        Write-Host "   Expected: $expectedEndpoint" -ForegroundColor Green
        $needsUpdate = $true
    }
    
    if ($currentRegion -ne $expectedRegion) {
        Write-Host "⚠️  SPEECH_REGION is wrong!" -ForegroundColor Red
        Write-Host "   Current:  $currentRegion" -ForegroundColor Red
        Write-Host "   Expected: $expectedRegion" -ForegroundColor Green
        $needsUpdate = $true
    }
    
    if (-not $needsUpdate) {
        Write-Host "✅ All settings are correct!" -ForegroundColor Green
        exit 0
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    $response = Read-Host "Update Azure settings now? (y/n)"
    
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host ""
        Write-Host "Updating settings..." -ForegroundColor Yellow
        
        az functionapp config appsettings set `
            --name $FunctionAppName `
            --resource-group $ResourceGroup `
            --settings `
                "AZURE_OPENAI_ENDPOINT=$expectedEndpoint" `
                "SPEECH_REGION=$expectedRegion"
        
        Write-Host ""
        Write-Host "✅ Settings updated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  IMPORTANT: Restart the function app for changes to take effect" -ForegroundColor Yellow
        Write-Host ""
        
        $restart = Read-Host "Restart function app now? (y/n)"
        if ($restart -eq "y" -or $restart -eq "Y") {
            Write-Host "Restarting function app..." -ForegroundColor Yellow
            az functionapp restart --name $FunctionAppName --resource-group $ResourceGroup
            Write-Host "✅ Function app restarted!" -ForegroundColor Green
        }
    }
    
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}
