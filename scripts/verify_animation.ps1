param()
$ErrorActionPreference = 'Stop'
$animationProject = Split-Path -Parent $PSScriptRoot
Push-Location $animationProject
try {
    & .\gradlew.bat :app:testDebugUnitTest --tests com.bugworld.app.InsectAnimationTest --tests com.bugworld.app.AnimationClipPolicyTest --offline --console=plain
    exit $LASTEXITCODE
} finally { Pop-Location }
