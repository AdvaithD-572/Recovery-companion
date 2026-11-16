param([string]$Flutter = 'flutter', [string]$ApiBaseUrl = 'http://10.0.2.2:8000')
$ErrorActionPreference = 'Stop'
# This local signing identity can update sideloaded builds from this laptop.
# DPAPI protects the password under the current Windows user account.
$keys = Join-Path $env:LOCALAPPDATA 'RecoveryCompanion/signing'
New-Item -ItemType Directory -Force -Path $keys | Out-Null
$store = Join-Path $keys 'patient.p12'
$protected = Join-Path $keys 'password.dpapi'
if ((Test-Path $store) -ne (Test-Path $protected)) { throw 'The local signing identity is incomplete. Restore the original pair before updating.' }
$env:RC_KEY_ALIAS = 'patient'
try {
    if (-not (Test-Path $store)) {
        $bytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $env:RC_STORE_PASSWORD = [Convert]::ToBase64String($bytes)
        $secure = ConvertTo-SecureString -AsPlainText $env:RC_STORE_PASSWORD -Force
        $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $protected
        & "$env:JAVA_HOME/bin/keytool.exe" -genkeypair -keystore $store -storetype PKCS12 -storepass:env RC_STORE_PASSWORD -alias patient -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=Recovery Companion Local Distribution'
        if ($LASTEXITCODE) { throw 'Android signing identity creation failed.' }
    } else {
        $secure = (Get-Content -Raw -LiteralPath $protected).Trim() | ConvertTo-SecureString
        $env:RC_STORE_PASSWORD = [Net.NetworkCredential]::new('', $secure).Password
    }
    $env:RC_KEYSTORE = $store
    $env:RC_KEY_PASSWORD = $env:RC_STORE_PASSWORD
    & "$PSScriptRoot/build-android.ps1" -Flutter $Flutter -ApiBaseUrl $ApiBaseUrl -Release
} finally {
    foreach ($name in 'RC_STORE_PASSWORD','RC_KEY_PASSWORD','RC_KEYSTORE','RC_KEY_ALIAS') {
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
}
