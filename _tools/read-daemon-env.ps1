$sig = @'
using System;
using System.Runtime.InteropServices;
public class EnvProbe {
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern IntPtr OpenProcess(int access, bool inherit, int pid);
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out IntPtr read);
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern bool CloseHandle(IntPtr h);
  [DllImport("ntdll.dll")]
  public static extern int NtQueryInformationProcess(IntPtr h, int cls, byte[] info, int len, out int ret);
}
'@
Add-Type -TypeDefinition $sig -ErrorAction Stop

function Get-RemoteEnv([int]$ProcessId) {
  $h = [EnvProbe]::OpenProcess(0x0410, $false, $ProcessId)   # VM_READ | QUERY_INFORMATION
  if ($h -eq [IntPtr]::Zero) { return @{ error = "OpenProcess failed: $([ComponentModel.Win32Exception]::new([Runtime.InteropServices.Marshal]::GetLastWin32Error()).Message)" } }
  try {
    # PROCESS_BASIC_INFORMATION: PebBaseAddress is at offset 8 on x64
    $pbi = New-Object byte[] 48
    $ret = 0
    if ([EnvProbe]::NtQueryInformationProcess($h, 0, $pbi, 48, [ref]$ret) -ne 0) { return @{ error = 'NtQueryInformationProcess failed' } }
    $peb = [BitConverter]::ToInt64($pbi, 8)
    # PEB->ProcessParameters at 0x20
    $ppBuf = New-Object byte[] 8
    [void][EnvProbe]::ReadProcessMemory($h, [IntPtr]($peb + 0x20), $ppBuf, 8, [ref]$ret)
    $pp = [BitConverter]::ToInt64($ppBuf, 0)
    # RTL_USER_PROCESS_PARAMETERS->Environment at 0x80 (x64)
    $envBuf = New-Object byte[] 8
    [void][EnvProbe]::ReadProcessMemory($h, [IntPtr]($pp + 0x80), $envBuf, 8, [ref]$ret)
    $envPtr = [BitConverter]::ToInt64($envBuf, 0)
    # read up to 256KB of environment block
    $size = 256 * 1024
    $data = New-Object byte[] $size
    $got = [IntPtr]::Zero
    [void][EnvProbe]::ReadProcessMemory($h, [IntPtr]$envPtr, $data, $size, [ref]$got)
    $n = [int]$got
    if ($n -le 0) { return @{ error = 'environment read returned 0 bytes' } }
    $text = [Text.Encoding]::Unicode.GetString($data, 0, $n)
    $vars = @()
    foreach ($chunk in ($text -split "`0`0")[0] -split "`0") {
      if ($chunk -match '=') { $vars += $chunk }
    }
    return @{ vars = $vars; bytes = $n }
  } finally { [void][EnvProbe]::CloseHandle($h) }
}

foreach ($procId in 3288, 2740, 28640) {
  "################ PID $procId ################"
  $r = Get-RemoteEnv $procId
  if ($r.error) { "  ERROR: $($r.error)"; continue }
  "  (read $($r.bytes) bytes, $($r.vars.Count) vars)"
  $interesting = $r.vars | Where-Object { $_ -match 'CODEBUDDY|WORKBUDDY|AT_REST|SIDECAR|CREDENTIAL|PREWARM|ACC_PRODUCT' }
  if ($interesting) { "  --- credential/protection related ---"; $interesting | ForEach-Object { "    $_" } }
  else { "  (no credential/protection vars found)" }
  ""
}
