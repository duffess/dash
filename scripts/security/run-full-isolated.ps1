param([ValidateSet('python','frontend','probe')][string]$Component='python')
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$tooling='C:\Users\guidu\security-audit-skill\dashflow\run-1\stabilization-20261022'
$run=Join-Path $tooling ('isolated-full-'+$Component+'-'+[guid]::NewGuid().ToString('N'))
$snapshot=Join-Path $run 'source'
New-Item -ItemType Directory -Path $snapshot,(Join-Path $run 'rootfs'),(Join-Path $snapshot 'my-app\node_modules') -Force | Out-Null
$files=@()
$files+=Get-Item -LiteralPath (Join-Path $repo 'scripts\security\frontend-probe.mjs')
$files+=Get-Item -LiteralPath (Join-Path $repo 'scripts\security\frontend-build.mjs')
foreach($folder in @('app','tests','scripts\maintenance','alembic')){
    $files+=Get-ChildItem -LiteralPath (Join-Path $repo $folder) -Recurse -File -Filter '*.py'
}
foreach($folder in @('my-app\src','my-app\public')){
    $files+=Get-ChildItem -LiteralPath (Join-Path $repo $folder) -Recurse -File
}
foreach($name in @('package.json','package-lock.json','index.html','vite.config.ts','tailwind.config.js','postcss.config.js')){
    $files+=Get-Item -LiteralPath (Join-Path $repo ('my-app\'+$name))
}
$total=0
foreach($file in $files){
    if($file.Attributes -band [IO.FileAttributes]::ReparsePoint -or $file.Length -gt 8MB){throw 'Unexpected source file'}
    $relative=$file.FullName.Substring($repo.Length+1)
    if($relative -match '(^|\\)\.env|(^|\\)__pycache__|(^|\\)node_modules\\'){throw 'Forbidden source path'}
    $total+=$file.Length
    if($total -gt 32MB){throw 'Source snapshot exceeds bound'}
    $destination=Join-Path $snapshot $relative
    New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination
}
# Reviewed configuration: no database credentials copied into the snapshot.
$ini=[IO.File]::ReadAllText((Join-Path $repo 'alembic.ini'))
$ini=[regex]::Replace($ini,'(?m)^sqlalchemy\.url\s*=.*$','sqlalchemy.url = sqlite://')
[IO.File]::WriteAllText((Join-Path $snapshot 'alembic.ini'),$ini)
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'full-sandbox.c') -Destination (Join-Path $run 'full-sandbox.c')
function LinuxPath([string]$value){
    $mapped=& wsl.exe -d Ubuntu-22.04 -- wslpath -a ($value.Replace('\','/'))
    if($LASTEXITCODE -ne 0){throw 'WSL path conversion failed'}
    return $mapped.Trim()
}
$linuxRun=LinuxPath $run
$linuxSource=LinuxPath $snapshot
$linuxPython=LinuxPath (Join-Path $tooling 'python\cpython-3.11-linux-x86_64-gnu')
$linuxDeps=LinuxPath (Join-Path $tooling 'deps')
$linuxNode=LinuxPath (Join-Path $tooling 'tooling\node-v24.22.1-linux-x64')
$linuxModules=LinuxPath (Join-Path $tooling 'frontend-deps\node_modules')
& wsl.exe -d Ubuntu-22.04 -- env -i PATH=/usr/bin:/bin timeout 30 gcc -O2 -Wall -Wextra -Werror "$linuxRun/full-sandbox.c" -o "$linuxRun/full-sandbox"
if($LASTEXITCODE -ne 0){throw 'Trusted launcher compilation failed'}
# Retain namespace-only mount capabilities for the reviewed launcher. It drops
# every capability before exec. Real UID stays non-root for RLIMIT_NPROC.
& wsl.exe -d Ubuntu-22.04 -- env -i PATH=/usr/bin:/bin timeout --kill-after=3 120 unshare --user --map-current-user --keep-caps --mount --net --pid --fork --kill-child "$linuxRun/full-sandbox" "$linuxRun/rootfs" $linuxSource $linuxPython $linuxDeps $linuxNode $linuxModules $Component
$testExit=$LASTEXITCODE
Write-Host "Full isolated $Component exit: $testExit. Snapshot: $run"
Write-Host 'No target-produced files are retained; scratch tmpfs is discarded.'
if($testExit -ne 0){throw 'Full isolated run failed. Host fallback is forbidden.'}
