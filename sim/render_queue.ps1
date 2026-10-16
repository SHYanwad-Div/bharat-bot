# Render every shot (resumable), fill any frames lost to crashes, and encode MP4s for the film.
#   pwsh -File sim/render_queue.ps1
param([string[]]$Shots = @('bharat_full', 'baseline_pothole', 'baseline_dogs', 'baseline_theft', 'us_sidewalk'),
      [string]$Res = '1280x720', [int]$Samples = 16)
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$B = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$FF = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe | Select-Object -First 1).FullName
New-Item -ItemType Directory -Force renders\logs, videos, video\public\clips | Out-Null

# let a render that is already running finish first
while (Get-CimInstance Win32_Process -Filter "Name='blender.exe'" | Where-Object { $_.CommandLine -match 'render_shot' }) {
  Start-Sleep -Seconds 20
}
foreach ($shot in $Shots) {
  foreach ($pass in 1, 2) {
    Get-ChildItem "renders\$shot" -Filter f_*.jpg -ErrorAction SilentlyContinue | Where-Object Length -eq 0 | Remove-Item
    & $B -b "blend\$shot.blend" --python sim\render_shot.py -- --out "renders\$shot" --res $Res --samples $Samples *>> "renders\logs\$shot.queue.log"
  }
  & $FF -v error -y -framerate 30 -start_number 1 -i "renders\$shot\f_%04d.jpg" -c:v libx264 -pix_fmt yuv420p -crf 17 `
    -g 30 -movflags +faststart "videos\$shot.mp4"
  Copy-Item "videos\$shot.mp4" "video\public\clips\$shot.mp4" -Force
  $n = (Get-ChildItem "renders\$shot" -Filter f_*.jpg | Where-Object Length -gt 0).Count
  "{0} {1}: {2} frames -> videos\{1}.mp4" -f (Get-Date -Format HH:mm:ss), $shot, $n
}
"ALL SHOTS DONE $(Get-Date -Format HH:mm:ss)"
