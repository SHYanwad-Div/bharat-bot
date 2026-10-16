# Ask Windows not to idle-sleep while a given process (e.g. the render queue) is alive, then release.
# Uses SetThreadExecutionState like a video player does; no power settings are changed.
#   pwsh -File sim/keep_awake_while.ps1 -WatchPid 1234
param([Parameter(Mandatory)][int]$WatchPid)
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
$continuous = [uint32]2147483648      # ES_CONTINUOUS
$system = [uint32]1                   # ES_SYSTEM_REQUIRED
[void][Win32.Power]::SetThreadExecutionState($continuous -bor $system)
while (Get-Process -Id $WatchPid -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 30 }
[void][Win32.Power]::SetThreadExecutionState($continuous)
