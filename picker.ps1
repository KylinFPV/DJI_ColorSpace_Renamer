# 原生文件夹选择（独立进程，最稳版本）
# 说明：不用 FolderBrowserDialog（在新版 Windows + 无宿主窗体时常常静默不弹），
# 改用 OpenFileDialog 选任意文件后取其所在目录；该对话框是标准顶层窗口，必然可见。
# 编码：本文件必须保存为 UTF-8 with BOM。Windows PowerShell 5.1 读取无 BOM 的 .ps1
#       会按系统 ANSI(GBK) 解码，下面这些中文提示会全部变成乱码。
#       app.py 的 launch_picker() 还有一道运行时自愈，BOM 意外丢失也能补上。
$ErrorActionPreference = 'Stop'

# 无 BOM 的 UTF-8：Python 端 read_text('utf-8') 后 os.path.isdir 首次判断即可成功，
# 也不会在中文路径前面带上 \ufeff。PS5.1 的 Set-Content -Encoding UTF8 会写 BOM，故不用它。
$utf8 = New-Object System.Text.UTF8Encoding($false)

$res = Join-Path $PSScriptRoot '_picker_result.txt'
$log = Join-Path $PSScriptRoot '_picker_error.txt'
Remove-Item -LiteralPath $res -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $log -ErrorAction SilentlyContinue

function Write-PickerText([string]$path, [string]$text) {
    [System.IO.File]::WriteAllText($path, $text, $utf8)
}

try {
    Add-Type -AssemblyName System.Windows.Forms

    $d = New-Object System.Windows.Forms.OpenFileDialog
    $d.Title = '选择一个文件以定位素材文件夹（或在文件名框粘贴路径后点“打开”）'
    $d.Filter = '视频文件 (*.MP4;*.LRF;*.MOV)|*.MP4;*.LRF;*.MOV|所有文件 (*.*)|*.*'
    $d.CheckFileExists = $false
    $d.ValidateNames = $false
    $d.CheckPathExists = $true
    $d.FileName = '点“打开”即使用当前所在文件夹'
    $d.RestoreDirectory = $false

    $r = $d.ShowDialog()
    if ($r -eq [System.Windows.Forms.DialogResult]::OK -and $d.FileName) {
        $dir = [System.IO.Path]::GetDirectoryName($d.FileName)
        if ($dir -and (Test-Path -LiteralPath $dir)) {
            Write-PickerText $res $dir
        } else {
            $dir2 = $d.FileName
            if (Test-Path -LiteralPath $dir2) {
                Write-PickerText $res $dir2
            } else {
                Write-PickerText $log ('目录无效: ' + $d.FileName)
            }
        }
    } else {
        # 用户取消：写标记让前端立即停止轮询，不必等到超时
        Write-PickerText $log '已取消选择'
    }
} catch {
    Write-PickerText $log ($_.Exception.ToString())
}
