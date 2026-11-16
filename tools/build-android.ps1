param([string]$ApiBaseUrl='http://10.0.2.2:8000',[string]$Flutter='flutter',[switch]$Release)
$ErrorActionPreference = 'Stop'
if ($Release) {
    if (-not $ApiBaseUrl.StartsWith('https://') -and $ApiBaseUrl -notin @('http://127.0.0.1:8000','http://10.0.2.2:8000')) { throw 'Choose HTTPS or a local test endpoint.' }
    foreach ($setting in 'RC_KEYSTORE','RC_STORE_PASSWORD','RC_KEY_ALIAS','RC_KEY_PASSWORD') {
        if (-not [Environment]::GetEnvironmentVariable($setting)) { throw "Configure $setting for release signing." }
    }
}
$root = Split-Path $PSScriptRoot -Parent
# Android-only staging avoids desktop plugin symlinks and non-ASCII Gradle paths.
$stage = Join-Path ([IO.Path]::GetTempPath()) ('rc-build-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $stage | Out-Null
foreach ($name in 'android','assets','lib','pubspec.yaml','pubspec.lock','test') {
    Copy-Item -LiteralPath (Join-Path "$root/mobile" $name) -Destination $stage -Recurse
}
if ($env:RC_GRADLE_ARCHIVE) {
    $wrapper = Join-Path $stage 'android/gradle/wrapper/gradle-wrapper.properties'
    $archive = (Resolve-Path -LiteralPath $env:RC_GRADLE_ARCHIVE).Path
    $url = ([uri]$archive).AbsoluteUri
    (Get-Content -Raw $wrapper) -replace '(?m)^distributionUrl=.*$', "distributionUrl=$url" | Set-Content $wrapper
}
Push-Location $stage
try {
    & $Flutter pub get
    if ($LASTEXITCODE) { throw 'Dependency resolution failed' }
    & $Flutter test
    if ($LASTEXITCODE) { throw 'Mobile tests failed' }
    $mode = if ($Release) { '--release' } else { '--debug' }
    & $Flutter build apk $mode "--dart-define=API_BASE_URL=$ApiBaseUrl"
    if ($LASTEXITCODE) { throw 'APK compilation failed' }
    $out = Join-Path $root 'dist'
    New-Item -ItemType Directory -Force $out | Out-Null
    Copy-Item build/app/outputs/flutter-apk/app-*.apk $out
    Get-ChildItem $out -Filter '*.apk'
} finally { Pop-Location }
