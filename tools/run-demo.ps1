param([switch]$Android, [string]$Avd)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root 'backend/venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create the Python environment using the README first.' }

if ($Android) {
    $apk = Join-Path $root 'dist/app-debug.apk'
    if (-not (Test-Path -LiteralPath $apk)) { throw 'Build the demo APK with tools/build-android.ps1 first.' }
    $locations = @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT, "$env:TEMP/recovery-android-tools/sdk", "$env:LOCALAPPDATA/Android/Sdk")
    $sdk = $locations | Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ 'emulator/emulator.exe')) } | Select-Object -First 1
    if (-not $sdk) { throw 'Install the Android SDK and create an emulator, or run without -Android for the clinic desk.' }
    $env:ANDROID_HOME = $sdk
    $env:ANDROID_SDK_ROOT = $sdk
    if ($sdk -eq "$env:TEMP/recovery-android-tools/sdk" -and (Test-Path "$env:TEMP/recovery-android-tools/avds")) {
        $env:ANDROID_AVD_HOME = "$env:TEMP/recovery-android-tools/avds"
    }
    $adb = Join-Path $sdk 'platform-tools/adb.exe'
    $emulator = Join-Path $sdk 'emulator/emulator.exe'
    if (-not $Avd) { $Avd = (& $emulator -list-avds | Select-Object -First 1) }
    if (-not $Avd) { throw 'Create an Android virtual device and try again.' }
    function Get-DemoDevice {
        foreach ($line in (& $adb devices)) {
            if ($line -match '^(emulator-\d+)\s+device$') {
                $serial = $Matches[1]
                if ((& $adb -s $serial emu avd name | Select-Object -First 1) -eq $Avd) { return $serial }
            }
        }
    }
    $device = Get-DemoDevice
    if (-not $device) {
        Write-Host "Starting Android emulator $Avd. A cold boot can take several minutes."
        Start-Process -FilePath $emulator -ArgumentList @('-avd', $Avd, '-no-snapshot-load') -WindowStyle Normal
    }
    $deadline = (Get-Date).AddMinutes(8)
    do {
        $device = Get-DemoDevice
        if ($device -and ((& $adb -s $device shell getprop sys.boot_completed) -match '^1')) { break }
        if ((Get-Date) -gt $deadline) { throw 'The selected emulator did not finish booting.' }
        Start-Sleep -Seconds 3
    } while ($true)
    & $adb -s $device install -r $apk
    if ($LASTEXITCODE) { throw 'The Android package did not install.' }
    & $adb -s $device shell am start -n com.example.recovery_companion/.MainActivity
}
Push-Location (Join-Path $root 'backend')
try { & $python -u demo.py } finally { Pop-Location }
