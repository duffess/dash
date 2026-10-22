param(
    [string]$Distribution = 'Ubuntu-22.04',
    [string]$ScratchParent = 'C:\Users\guidu\security-audit-skill\dashflow\run-1\remediation'
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not (Test-Path -LiteralPath (Join-Path $repo 'app\main.py'))) { throw 'Repository not found' }
$parent = [IO.Path]::GetFullPath($ScratchParent)
if ($parent.StartsWith($repo + '\', [StringComparison]::OrdinalIgnoreCase) -or $parent -eq $repo) {
    throw 'Scratch must be outside the repository'
}
$run = Join-Path $parent ('isolated-' + [guid]::NewGuid().ToString('N'))
$snapshot = Join-Path $run 'source'
$rootfs = Join-Path $run 'rootfs'
New-Item -ItemType Directory -Path $snapshot, $rootfs -Force | Out-Null

# Explicit source-only allowlist: never copy .env, databases, Git or venvs.
$files = @()
foreach ($folder in @('app', 'app\routers', 'app\utils', 'app\models', 'app\schemas', 'tests', 'scripts\maintenance')) {
    $files += Get-ChildItem -LiteralPath (Join-Path $repo $folder) -File -Filter '*.py'
}
foreach ($relative in @('my-app\src\contexts\AuthContext.jsx', 'my-app\src\pages\Dashboard.jsx',
                         'my-app\src\pages\Reports.jsx', 'my-app\src\reports\DemoReport.jsx')) {
    $files += Get-Item -LiteralPath (Join-Path $repo $relative)
}
foreach ($file in $files) {
    if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Symlinked source is not accepted' }
    $relative = $file.FullName.Substring($repo.Length + 1)
    $destination = Join-Path $snapshot $relative
    New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination
}
# Trusted, reviewed launcher only. Do not run modified launchers without review.
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'sandbox.c') -Destination (Join-Path $run 'sandbox.c')
function LinuxPath([string]$PathValue) {
    $converted = & wsl.exe -d $Distribution -- wslpath -a ($PathValue.Replace('\', '/'))
    if ($LASTEXITCODE -ne 0) { throw 'Cannot map the scratch path into WSL' }
    return $converted.Trim()
}
$linuxRun = LinuxPath $run
$linuxSource = LinuxPath $snapshot
$linuxRoot = LinuxPath $rootfs
& wsl.exe -d $Distribution -- env -i PATH=/usr/bin:/bin timeout 30 gcc -O2 -Wall -Wextra -Werror "$linuxRun/sandbox.c" -o "$linuxRun/sandbox"
if ($LASTEXITCODE -ne 0) { throw 'Trusted sandbox compilation failed. No dependencies will be installed.' }
& wsl.exe -d $Distribution -- env -i PATH=/usr/bin:/bin timeout --kill-after=2 45 unshare --user --map-root-user --mount --net --pid --fork --kill-child "$linuxRun/sandbox" $linuxRoot $linuxSource
$testExit = $LASTEXITCODE
Write-Host "Isolated test exit: $testExit. Disposable source copy: $run"
Write-Host 'No result files are promoted. The tmpfs is released with the namespace.'
if ($testExit -ne 0) { throw "Isolated tests failed ($testExit). Host execution is not used as a fallback." }
