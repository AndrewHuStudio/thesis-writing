using Eto.Forms;
using Rhino;

namespace OutpatientRhino;

public sealed partial class OutpatientPanel
{
    private readonly UITimer refreshTimer = new() { Interval = 0.75 };
    private const string DirectoryReadError = "后端目录暂时无法读取，正在等待恢复。";
    private bool directoryUnreadable;
    private string? backendDirectory;
    private string? observedFiles;
    private bool refreshPending;
    private bool trackLocalPreview;

    private void ConnectRefresh()
    {
        var root = BackendClient.FindRoot();
        backendDirectory = root is null ? null : Path.Combine(root, "s-门诊平面生成系统", "backend");
        observedFiles = null;
        refreshPending = false;
        directoryUnreadable = false;
        if (root is null)
            ShowStatus("请在「＋」中设置项目目录。");
        CheckBackend(this, EventArgs.Empty);
    }

    private async void CheckBackend(object? sender, EventArgs args)
    {
        if (backendDirectory is null)
            return;
        string snapshot;
        try
        {
            snapshot = string.Join("\n", new DirectoryInfo(backendDirectory).EnumerateFiles("*.py")
                .OrderBy(file => file.Name, StringComparer.Ordinal)
                .Select(file => $"{file.Name}:{file.Length}:{file.LastWriteTimeUtc.Ticks}"));
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            if (!directoryUnreadable) ShowStatus(DirectoryReadError);
            directoryUnreadable = true;
            refreshPending = true;
            return;
        }
        if (directoryUnreadable && status.Text == DirectoryReadError) ShowStatus("");
        directoryUnreadable = false;
        if (snapshot != observedFiles)
        {
            refreshPending |= observedFiles is not null;
            observedFiles = snapshot;
            return; // Wait for one stable sample after a save or rename.
        }
        if (!refreshPending || running is not null)
            return;
        refreshPending = false;
        if (trackLocalPreview && confirmed && !written && useAdvice.Checked != true &&
            boundary?.Document == RhinoDoc.ActiveDoc?.RuntimeSerialNumber && boundary is not null)
            await GenerateAsync();
    }
}
