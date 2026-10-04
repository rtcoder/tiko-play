# Integration test for disposable GitHub-hosted Windows runners only.
param(
    [Parameter(Mandatory)][string]$Installer,
    [Parameter(Mandatory)][string]$PreviousInstaller,
    [Parameter(Mandatory)][string]$Version
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'Run only on a disposable GitHub-hosted Windows runner, never on a personal machine.'
}
$Installer = (Resolve-Path $Installer).Path
$PreviousInstaller = (Resolve-Path $PreviousInstaller).Path
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\TikoPlay'
$dataDir = Join-Path $env:APPDATA 'TikoPlay'
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'TikoPlay.lnk'
$startLink = Join-Path ([Environment]::GetFolderPath('Programs')) 'TikoPlay\TikoPlay.lnk'
# Keep the original 32-bit installer registry view to support existing releases.
$registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{163C1D39-E804-433C-B0DB-5E43F8366D09}_is1'
$logs = Join-Path $env:RUNNER_TEMP 'installer-logs'
New-Item -ItemType Directory -Force $logs | Out-Null
foreach ($path in @($installDir, $dataDir, $desktopLink, $startLink, $registry)) {
    if (Test-Path $path) { throw "Test requires clean state: $path" }
}

function Assert-That([bool]$Condition, [string]$Message) {
    if (!$Condition) { throw $Message }
}
function Invoke-Setup([string]$Exe, [string]$Label, [string[]]$Extra = @()) {
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/SP-', '/NORESTART', '/RESTARTEXITCODE=3010', "/LOG=`"$logs\$Label.log`"") + $Extra
    $process = Start-Process -FilePath $Exe -ArgumentList $arguments -PassThru
    if (!$process.WaitForExit(180000)) { throw "Installer timed out: $Label" }
    Assert-That ($process.ExitCode -eq 0) "$Label failed: exit $($process.ExitCode)"
}
function Assert-Installed {
    Assert-That (Test-Path "$installDir\TikoPlay.exe") 'Missing executable'
    Assert-That (Test-Path $startLink) 'Missing Start menu shortcut'
    $shell = New-Object -ComObject WScript.Shell
    Assert-That ($shell.CreateShortcut($startLink).TargetPath -eq "$installDir\TikoPlay.exe") 'Wrong shortcut target'
    Assert-That ((Get-ItemProperty $registry).DisplayVersion -eq $Version) 'Wrong installed version'
    Assert-That ((Get-FileHash "$installDir\TikoPlay.exe").Hash -eq (Get-FileHash 'dist\TikoPlay\TikoPlay.exe').Hash) 'Installed executable differs from build'
}
function Assert-Data {
    foreach ($name in $script:dataHashes.Keys) {
        Assert-That ((Get-FileHash "$dataDir\$name").Hash -eq $script:dataHashes[$name]) "Changed user data: $name"
    }
}
function Remove-Installed([string]$Label) {
    Invoke-Setup "$installDir\unins000.exe" $Label
    # Inno's uninstaller may exit its parent before the temporary child finishes.
    $deadline = (Get-Date).AddSeconds(30)
    while (((Test-Path "$installDir\TikoPlay.exe") -or (Test-Path $registry)) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 250
    }
    Assert-That (!(Test-Path "$installDir\TikoPlay.exe")) 'Executable remains after uninstall'
    Assert-That (!(Test-Path $registry)) 'Uninstall registration remains'
    Assert-That (!(Test-Path $desktopLink)) 'Desktop shortcut remains'
    Assert-That (!(Test-Path $startLink)) 'Start menu shortcut remains'
    Assert-Data
}

# A missing Tasks binding would make this fresh-install check fail.
Invoke-Setup $Installer 'fresh-pl' @('/LANG=polish')
Assert-Installed
Assert-That (!(Test-Path $desktopLink)) 'Desktop shortcut created without opting in'
New-Item -ItemType Directory -Force $dataDir | Out-Null
# Fixture bytes never reach a running app; this checks installer data preservation.
$script:dataHashes = @{}
foreach ($name in @('config.json', 'preferences.json', 'overlay.json', 'config.v6.backup.json')) {
    Set-Content -LiteralPath "$dataDir\$name" -Value ('{"installer_test":"' + $name + '"}') -Encoding utf8
    $script:dataHashes[$name] = (Get-FileHash "$dataDir\$name").Hash
}
Remove-Installed 'uninstall-fresh'

# Use a real earlier published installer, in a non-default path with spaces.
$installDir = Join-Path $env:RUNNER_TEMP 'TikoPlay upgrade test'
Invoke-Setup $PreviousInstaller 'previous' @("/DIR=`"$installDir`"")
Assert-Data
# Earlier versions create this unconditionally; do not mistake it for new behavior.
if (Test-Path $desktopLink) { Remove-Item -LiteralPath $desktopLink }
Invoke-Setup $Installer 'upgrade-en' @('/LANG=english', '/TASKS=desktopicon')
Assert-Installed
Assert-Data
Assert-That (Test-Path $desktopLink) 'Opted-in desktop shortcut missing'
Assert-That (!(Test-Path "$env:LOCALAPPDATA\Programs\TikoPlay\TikoPlay.exe")) 'Upgrade created a second installation'
Remove-Item -LiteralPath $desktopLink
Invoke-Setup $Installer 'reinstall' @('/LANG=english')
Assert-Installed
Assert-Data
Assert-That (Test-Path $desktopLink) 'Reinstall did not remember the desktop shortcut choice'

# Start the installed frozen binary on isolated data; never start LIVE or send keys.
$runtimeData = Join-Path $env:RUNNER_TEMP 'tikoplay-runtime-test'
New-Item -ItemType Directory -Force $runtimeData | Out-Null
Set-Content "$runtimeData\preferences.json" '{"language":"en"}' -Encoding utf8NoBOM
$appProcess = Start-Process "$installDir\TikoPlay.exe" -ArgumentList @('--data-dir', "`"$runtimeData`"") -PassThru
try {
    $ready = $false
    $deadline = (Get-Date).AddSeconds(45)
    while (!$ready -and (Get-Date) -lt $deadline) {
        $appProcess.Refresh()
        Assert-That (!$appProcess.HasExited) 'Installed application exited before becoming ready'
        $connections = @(Get-NetTCPConnection -State Listen -OwningProcess $appProcess.Id -ErrorAction SilentlyContinue)
        foreach ($connection in $connections) {
            if ($connection.LocalAddress -ne '127.0.0.1') { continue }
            $origin = "http://127.0.0.1:$($connection.LocalPort)"
            try {
                $health = Invoke-RestMethod "$origin/api/health" -TimeoutSec 2
                $page = Invoke-WebRequest "$origin/" -TimeoutSec 2
                $ready = $health.ready -and $page.StatusCode -eq 200 -and $page.Content.Contains('id="root"')
            } catch { continue }
            if ($ready) { break }
        }
        if (!$ready) { Start-Sleep -Milliseconds 500 }
    }
    Assert-That $ready 'Installed application did not serve health and panel'
} finally {
    # Test teardown only; not a graceful tray-shutdown acceptance test.
    if (!$appProcess.HasExited) { Stop-Process -Id $appProcess.Id -Force; $appProcess.WaitForExit() }
}
Remove-Installed 'uninstall-upgrade'
Write-Output 'PASS: fresh install PL, optional shortcut, previous-release upgrade EN, reinstall, frozen app startup, uninstall, user data preservation.'
