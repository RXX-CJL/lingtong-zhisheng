$outFile = "E:\output\disk_audit.txt"
$results = [System.Collections.ArrayList]::new()

# 1. Disk summary
$d = Get-PSDrive C
[void]$results.Add("=== DISK SUMMARY ===")
[void]$results.Add("Total_GB: " + [math]::Round(($d.Used + $d.Free)/1GB,1))
[void]$results.Add("Used_GB: " + [math]::Round($d.Used/1GB,1))
[void]$results.Add("Free_GB: " + [math]::Round($d.Free/1GB,1))
[void]$results.Add("UsedPct: " + [math]::Round($d.Used/($d.Used+$d.Free)*100,1))
Write-Host "STEP1_DONE: Disk summary"

# 2. First-level dirs (skip Windows, $Recycle.Bin, System Volume Information)
[void]$results.Add("")
[void]$results.Add("=== FIRST-LEVEL DIRECTORIES ===")
$skipNames = @('Windows','$Recycle.Bin','System Volume Information')
$allDirs = Get-ChildItem 'C:\' -Directory -Force -EA SilentlyContinue | Where-Object { $skipNames -notcontains $_.Name }
$dirSizes = [System.Collections.ArrayList]::new()
foreach ($dir in $allDirs) {
    $s = (Get-ChildItem $dir.FullName -Recurse -Force -File -EA SilentlyContinue | Measure-Object Length -Sum -EA SilentlyContinue).Sum
    if ($null -eq $s) { $s = 0 }
    [void]$dirSizes.Add([PSCustomObject]@{Path=$dir.FullName; SizeGB=[math]::Round($s/1GB,2); SizeBytes=[long]$s})
    Write-Host ("DIR: " + $dir.Name + " = " + [math]::Round($s/1GB,2) + " GB")
}
$dirSizes | Sort-Object SizeBytes -Descending | ForEach-Object { [void]$results.Add(("{0}`t{1}" -f $_.SizeGB, $_.Path)) }
Write-Host "STEP2_DONE: First-level dirs"

# 3. Windows (excl WinSxS)
[void]$results.Add("")
[void]$results.Add("=== WINDOWS ===")
$s = (Get-ChildItem 'C:\Windows' -Force -File -EA SilentlyContinue | Measure-Object Length -Sum -EA SilentlyContinue).Sum
if ($null -eq $s) { $s = 0 }
Get-ChildItem 'C:\Windows' -Directory -Force -EA SilentlyContinue | Where-Object { $_.Name -ne 'WinSxS' } | ForEach-Object {
    $sub = (Get-ChildItem $_.FullName -Recurse -Force -File -EA SilentlyContinue | Measure-Object Length -Sum -EA SilentlyContinue).Sum
    if ($null -eq $sub) { $sub = 0 }
    $s += $sub
}
[void]$results.Add(("{0}`tC:\Windows (excl WinSxS)" -f [math]::Round($s/1GB,2)))
Write-Host ("STEP3_DONE: Windows = " + [math]::Round($s/1GB,2) + " GB")

# 4. Second-level for top 6
[void]$results.Add("")
[void]$results.Add("=== SECOND-LEVEL BREAKDOWN (Top 6) ===")
$top6 = $dirSizes | Sort-Object SizeBytes -Descending | Select-Object -First 6
foreach ($d in $top6) {
    [void]$results.Add("")
    [void]$results.Add("--- " + $d.Path + " (" + $d.SizeGB + " GB) ---")
    $subs = Get-ChildItem $d.Path -Directory -Force -EA SilentlyContinue | ForEach-Object {
        $s2 = (Get-ChildItem $_.FullName -Recurse -Force -File -EA SilentlyContinue | Measure-Object Length -Sum -EA SilentlyContinue).Sum
        if ($null -eq $s2) { $s2 = 0 }
        [PSCustomObject]@{Sub=$_.FullName; GB=[math]::Round($s2/1GB,2); B=[long]$s2}
    } | Sort-Object B -Descending | Select-Object -First 10
    foreach ($sub in $subs) { [void]$results.Add(("{0}`t{1}" -f $sub.GB, $sub.Sub)) }
    Write-Host ("STEP4_PART: " + $d.Path + " done")
}
Write-Host "STEP4_DONE: Second-level breakdown"

# 5. Files > 500MB
[void]$results.Add("")
[void]$results.Add("=== FILES > 500MB ===")
$bigFiles = Get-ChildItem 'C:\' -Recurse -Force -File -EA SilentlyContinue | Where-Object { $_.Length -gt 524288000 } | Sort-Object Length -Descending
foreach ($f in $bigFiles) {
    [void]$results.Add(("{0}`t{1}" -f [math]::Round($f.Length/1MB,0), $f.FullName))
}
Write-Host ("STEP5_DONE: Found " + @($bigFiles).Count + " large files")

# Write output
$results | Out-File $outFile -Encoding UTF8
Write-Host "ALL_DONE: Output at $outFile"
