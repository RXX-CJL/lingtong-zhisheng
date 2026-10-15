# 截取 CARLA 窗口画面（需要管理员权限：CARLA 以管理员身份运行，
# 否则 CopyFromScreen 会抛 "Access is denied"）
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$outDir = 'E:\output\_screenshots'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# 找到 CARLA 窗口（可能是 UE4 主窗口，也可能被 WindowsTerminal 托管）
$procs = Get-Process | Where-Object { $_.MainWindowTitle -ne '' -and $_.ProcessName -match 'CarlaUE4|Carla' }
if (-not $procs) {
    $procs = Get-Process | Where-Object { $_.MainWindowTitle -match 'CarlaUE4|CARLA' }
}
if (-not $procs) {
    Write-Output "NOT_FOUND: 没有找到标题含 CarlaUE4/CARLA 的窗口"
    Get-Process | Where-Object { $_.MainWindowTitle -ne '' } |
        Select-Object ProcessName, Id, MainWindowTitle | Format-Table -AutoSize | Out-String -Width 200
    exit 1
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

foreach ($p in $procs) {
    $h = $p.MainWindowHandle
    if ($h -eq 0) { continue }
    [void][W]::ShowWindow($h, 9)          # SW_RESTORE
    [void][W]::SetForegroundWindow($h)
    Start-Sleep -Milliseconds 900
    $r = New-Object W+RECT
    [void][W]::GetWindowRect($h, [ref]$r)
    $w = $r.Right - $r.Left
    $ht = $r.Bottom - $r.Top
    if ($w -le 0 -or $ht -le 0) { continue }
    $bmp = New-Object System.Drawing.Bitmap($w, $ht)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $ht)))
    $safe = ($p.ProcessName -replace '[^\w]', '_')
    $file = Join-Path $outDir ("carla_window_{0}_{1}x{2}.png" -f $safe, $w, $ht)
    $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Output ("SAVED: {0}  ({1}x{2})  pid={3}  title='{4}'" -f $file, $w, $ht, $p.Id, $p.MainWindowTitle)
}

# 另存一张全屏，便于确认窗口是否被遮挡
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp2 = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g2 = [System.Drawing.Graphics]::FromImage($bmp2)
$g2.CopyFromScreen($b.Left, $b.Top, 0, 0, (New-Object System.Drawing.Size($b.Width, $b.Height)))
$f2 = Join-Path $outDir 'desktop_full.png'
$bmp2.Save($f2, [System.Drawing.Imaging.ImageFormat]::Png)
$g2.Dispose(); $bmp2.Dispose()
Write-Output ("SAVED: {0}  ({1}x{2})" -f $f2, $b.Width, $b.Height)
