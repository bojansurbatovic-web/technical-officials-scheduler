# Makes the Microsoft Store package (MSIX) from a published app folder.
#   pwsh windows/store/make-msix.ps1 -Arch x64 -Version 1.0.1 -PublishDir windows/publish/x64 -OutDir windows/dist-store
# The Store signs the package itself; identity values come from identity.json (Partner Center → Product identity).
param(
  [Parameter(Mandatory)] [string] $Arch,
  [Parameter(Mandatory)] [string] $Version,
  [Parameter(Mandatory)] [string] $PublishDir,
  [Parameter(Mandatory)] [string] $OutDir
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$id = Get-Content (Join-Path $here 'identity.json') -Raw | ConvertFrom-Json

$tool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.*\x64\makeappx.exe" |
  Sort-Object { [version]$_.Directory.Parent.Name } | Select-Object -Last 1
if (-not $tool) { throw 'Windows SDK (makeappx.exe) not found' }
$bin = $tool.DirectoryName
"Windows SDK tools: $bin"

$parts = $Version.Split('.')
while ($parts.Count -lt 3) { $parts += '0' }
$v4 = ($parts[0..2] -join '.') + '.0'      # the Store needs the fourth number to be 0

$tmp = [IO.Path]::GetTempPath()
$layout = Join-Path $tmp "tos-msix-$Arch"
$pri = Join-Path $tmp "tos-pri-$Arch"
foreach ($d in @($layout, $pri)) { if (Test-Path $d) { Remove-Item $d -Recurse -Force } }
Copy-Item $PublishDir $layout -Recurse
Copy-Item (Join-Path $here 'Assets') (Join-Path $layout 'Assets') -Recurse

function Esc([string] $s) { [Security.SecurityElement]::Escape($s) }
$manifest = (Get-Content (Join-Path $here 'AppxManifest.template.xml') -Raw).
  Replace('{{NAME}}', (Esc $id.name)).Replace('{{PUBLISHER}}', (Esc $id.publisher)).
  Replace('{{PUBLISHER_DISPLAY}}', (Esc $id.publisherDisplayName)).Replace('{{VERSION}}', $v4).Replace('{{ARCH}}', $Arch)
Set-Content (Join-Path $layout 'AppxManifest.xml') $manifest -Encoding utf8

# resources.pri: lets Windows pick the right logo size (scale-200, targetsize-48 …)
New-Item -ItemType Directory $pri | Out-Null
Copy-Item (Join-Path $here 'Assets') (Join-Path $pri 'Assets') -Recurse
Copy-Item (Join-Path $layout 'AppxManifest.xml') $pri
& "$bin\makepri.exe" createconfig /cf "$pri\priconfig.xml" /dq en-US /pv 10.0.0 /o | Out-Null
if ($LASTEXITCODE) { throw 'makepri createconfig failed' }
& "$bin\makepri.exe" new /pr $pri /cf "$pri\priconfig.xml" /mn "$pri\AppxManifest.xml" /of (Join-Path $layout 'resources.pri') /o
if ($LASTEXITCODE) { throw 'makepri new failed' }

New-Item -ItemType Directory -Force $OutDir | Out-Null
$out = Join-Path (Resolve-Path $OutDir) "TechnicalOfficialsScheduler-$Version-$Arch.msix"
& "$bin\makeappx.exe" pack /d $layout /p $out /o
if ($LASTEXITCODE) { throw 'makeappx pack failed' }
"{0}  {1:N1} MB  ({2} {3})" -f (Split-Path $out -Leaf), ((Get-Item $out).Length / 1MB), $id.name, $v4
