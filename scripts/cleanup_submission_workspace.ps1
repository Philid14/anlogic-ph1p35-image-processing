param([switch]$Apply)
$ErrorActionPreference='Stop'
$workspaceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$backupRoot='D:\anlogic_project_backups\final_prep_20261103'
function WorkspacePath([string]$Relative) {
 $p=[IO.Path]::GetFullPath((Join-Path $workspaceRoot $Relative))
 if(-not $p.StartsWith($workspaceRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Outside workspace: $p"}
 if($p.StartsWith((Join-Path $workspaceRoot '.git')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Git database protected'}
 return $p
}
function BackupPath([string]$Relative) {
 $p=[IO.Path]::GetFullPath((Join-Path $backupRoot $Relative))
 if(-not $p.StartsWith($backupRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Outside named backup: $p"}
 return $p
}
$actions=[System.Collections.Generic.List[object]]::new()
function RecordMove([string]$Source,[string]$Target) {
 if(-not (Test-Path -LiteralPath $Source)){return}
 if((Get-Item -LiteralPath $Source -Force).LinkType){throw "Refuse junction move: $Source"}
 if(Test-Path -LiteralPath $Target){throw "Refuse overwrite: $Target"}
 $actions.Add([pscustomobject]@{action='move_preserve';source=$Source;destination=$Target})
 if($Apply){New-Item -ItemType Directory -Path (Split-Path $Target -Parent) -Force|Out-Null;Move-Item -LiteralPath $Source -Destination $Target}
}
function RecordDelete([string]$Relative) {
 $p=WorkspacePath $Relative
 if(-not (Test-Path -LiteralPath $p)){return}
 if((Get-Item -LiteralPath $p -Force).LinkType){throw "Refuse recursive junction deletion: $p"}
 $actions.Add([pscustomobject]@{action='delete_generated_or_retracted_demo';source=$p;destination=$null})
 if($Apply){Remove-Item -LiteralPath $p -Force -Recurse}
}
# Entire tmp is never deleted: one registered worktree is below it.
$tmpPath=WorkspacePath 'tmp'
foreach($folder in (Get-ChildItem -LiteralPath $tmpPath -Directory)) {
 if($folder.Name -eq 'technical_document_draft'){continue}
 if($folder.Name -eq 'latency_demo'){RecordDelete 'tmp\latency_demo';continue}
 RecordMove (WorkspacePath ('tmp\'+$folder.Name)) (BackupPath ('workspace_tmp\'+$folder.Name))
}
RecordDelete 'in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs'
RecordDelete 'edge_example\lab_ex2_edge_SC500_720P\lab_ex2_edge\td_project\camera_to_dsi_display_Runs'
foreach($f in Get-ChildItem -LiteralPath $workspaceRoot -File | Where-Object { $_.Name -match '^td_\d+_\d+\.logw?$' }) {
 RecordDelete $f.Name
}
foreach($f in Get-ChildItem -LiteralPath $workspaceRoot -File -Filter 'video_*.mp4') {
 RecordMove (WorkspacePath $f.Name) (WorkspacePath ('local_assets\recordings\'+$f.Name))
}
foreach($n in @('run_latency_actual_isp.py','run_latency_real_timing.py','tb_latency_actual_isp.sv','tb_latency_real_timing.sv')) {
 RecordMove (WorkspacePath ('tests\'+$n)) (BackupPath ('exploratory_tests\'+$n))
}
foreach($n in @('ALUMINUM_FRAME_VENDOR_RFQ_600_2026-10-24.md','MECHANICAL_MATERIALS_600_CUBE_2026-10-24.md','PROGRESS_REPORT_2026-10-21.md')) {
 RecordMove (WorkspacePath ('docs\'+$n)) (WorkspacePath ('local_assets\notes\'+$n))
}
$result=[pscustomobject]@{applied=[bool]$Apply;workspace=$workspaceRoot;backup=$backupRoot;protected_worktree='tmp/technical_document_draft/review-worktree';actions=$actions}
if($Apply){$result|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (WorkspacePath 'submission\WORKSPACE_CLEANUP.json') -Encoding utf8}
Write-Output ("Cleanup applied={0}; actions={1}; worktree preserved" -f $Apply,$actions.Count)
