using Eto.Forms;
using Eto.Drawing;

namespace OutpatientRhino;

internal sealed class BriefUpload : Panel
{
    private const string Prompt = "将任务书拖到这里，或点击选择文件";
    private readonly Button choose = new() { Text = Prompt, Height = 86, AllowDrop = true };
    private readonly Label hint = ChatTimeline.Text("支持 Word（.docx）、PDF 和 TXT，每次一份。", muted: true);
    private readonly Action<string> accept;

    internal BriefUpload(Action<string> accept)
    {
        this.accept = accept;
        choose.BackgroundColor = Color.FromArgb(245, 247, 246);
        choose.Click += (_, _) =>
        {
            using var picker = new OpenFileDialog { Title = "选择任务书", MultiSelect = false };
            picker.Filters.Add(new FileFilter("任务书", ".docx", ".pdf", ".txt"));
            if (picker.ShowDialog(this) == DialogResult.Ok) AcceptFiles([picker.FileName]);
        };
        choose.DragEnter += UpdateDragFeedback;
        choose.DragOver += UpdateDragFeedback;
        choose.DragLeave += (_, _) => Restore();
        choose.DragDrop += (_, e) =>
        {
            Restore();
            AcceptFiles(LocalFiles(e));
        };
        var column = ChatLayout.Column(5);
        column.Items.Add(choose);
        column.Items.Add(hint);
        Content = column;
    }

    private static string[] LocalFiles(DragEventArgs e) =>
        (e.Data.Uris ?? []).Where(uri => uri.IsAbsoluteUri && uri.IsFile).Select(uri => uri.LocalPath).ToArray();

    private static bool Supported(string path) =>
        Path.GetExtension(path).ToLowerInvariant() is ".docx" or ".pdf" or ".txt";

    private void UpdateDragFeedback(object? sender, DragEventArgs e)
    {
        var files = LocalFiles(e);
        var valid = files.Length == 1 && Supported(files[0]) && (e.AllowedEffects & DragEffects.Copy) != 0;
        e.Effects = valid ? DragEffects.Copy : DragEffects.None;
        choose.Text = valid ? "松开以添加任务书" : "请拖入一份 DOCX、PDF 或 TXT 文件";
        choose.BackgroundColor = valid ? Color.FromArgb(223, 247, 233) : Color.FromArgb(245, 247, 246);
    }

    private void Restore()
    {
        choose.Text = Prompt;
        choose.BackgroundColor = Color.FromArgb(245, 247, 246);
    }

    private void AcceptFiles(string[] files)
    {
        if (files.Length == 1 && Supported(files[0]) && File.Exists(files[0])) accept(files[0]);
        else hint.Text = "请选择一份可读取的 DOCX、PDF 或 TXT 文件。";
    }
}
