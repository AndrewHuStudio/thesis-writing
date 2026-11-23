using System.Runtime.InteropServices;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using Eto.Drawing;
using Eto.Forms;
using Rhino;
using Rhino.Geometry;

namespace OutpatientRhino;

[Guid("1d710de3-fcb6-478b-9b95-69231350ee79")]
public sealed partial class OutpatientPanel : Panel
{
    private readonly BackendClient backend = new();
    private readonly PlanPreview preview = new();
    private readonly ChatTimeline chat = new();
    private readonly Button add = ChatChrome.AddButton();
    private readonly ButtonMenuItem select = new() { Text = "选择边界" };
    private readonly ButtonMenuItem demo = new() { Text = "试用示例" };
    private readonly ButtonMenuItem configure = new() { Text = "设置项目目录" };
    private readonly ButtonMenuItem openBrief = new() { Text = "附加任务书" };
    private readonly ButtonMenuItem settings = new() { Text = "方案选项" };
    private readonly StackLayout options = ChatLayout.Column(5, 4);
    private readonly ButtonMenuItem editProgram = new() { Text = "手工录入清单" };
    private readonly Button composerAction = ChatChrome.ComposerActionButton();
    private readonly CheckBox useAdvice = new() { Text = "生成时使用 API 易布局建议" };
    private readonly CheckBox showOverlays = new() { Text = "预览中显示流线／视线" };
    private readonly DropDown entrance = new();
    private readonly TextArea composer = new() { Height = 58, Wrap = true, AcceptsTab = false };
    private string briefText = "";
    private string attachmentName = "";
    private readonly Label boundaryLabel = Note("先选择建筑边界，或载入内置 L 形示例。");
    private readonly Label programLabel = Note("尚未确认空间清单。");
    private readonly Label status = Note("");
    private AgentProgressCard? latestProgress;
    private Label? resultState;
    private Button? resultWrite, resultExport;
    private Button? draftEdit, draftGenerate;
    private BoundarySelection? boundary;
    private JsonObject? program;
    private JsonElement report;
    private RhinoPlan? plan;
    private CancellationTokenSource? running;
    private bool confirmed, written, loadingEntrance;
    private int revision;

    public OutpatientPanel()
    {
        Content = CreateChatPanel();
        WatchPinHost();
        ConnectRefresh();
        refreshTimer.Elapsed += CheckBackend;
        refreshTimer.Start();

        select.Click += (_, _) => RhinoApp.RunScript("_OutpatientSelectBoundary", false);
        demo.Click += async (_, _) => await SubmitAsync("生成一个 L 形示例");
        configure.Click += (_, _) => Safely(Configure);
        openBrief.Click += async (_, _) => await BriefDialogAsync();
        editProgram.Click += (_, _) => Safely(EditProgram);
        composer.TextChanged += (_, _) => UpdateComposerAction();
        composer.KeyDown += async (_, args) =>
        {
            if (args.Key != Keys.Enter || (args.Modifiers & Keys.Shift) != Keys.None)
                return;
            args.Handled = true;
            await SendFromComposerAsync();
        };
        composerAction.Click += async (_, _) =>
        {
            composer.Focus();
            if (running is null)
                await SendFromComposerAsync();
            else
            {
                running.Cancel();
                UpdateComposerAction();
            }
        };
        entrance.SelectedIndexChanged += (_, _) =>
        {
            if (loadingEntrance)
                return;
            preview.Edge = entrance.SelectedIndex;
            ClearPlan();
            ShowStatus("入口已更新。生成前请核对任务书与入口关系。");
        };
        showOverlays.CheckedChanged += (_, _) =>
        {
            preview.ShowOverlays = showOverlays.Checked == true;
            RhinoDoc.ActiveDoc?.Views.Redraw();
        };
        RhinoDoc.ActiveDocumentChanged += DocumentChanged;
        UpdateButtons();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            StopWatchingPinHost();
            refreshTimer.Stop();
            refreshTimer.Elapsed -= CheckBackend;
            refreshTimer.Dispose();
            RhinoDoc.ActiveDocumentChanged -= DocumentChanged;
            running?.Cancel();
            chat.ReleaseReplies();
            preview.Enabled = false;
        }
        base.Dispose(disposing);
    }

    private void DocumentChanged(object? sender, DocumentEventArgs args) =>
        Application.Instance.AsyncInvoke(() =>
        {
            UpdateButtons();
            if (boundary is not null && boundary.Document != RhinoDoc.ActiveDoc?.RuntimeSerialNumber)
                ShowStatus("已切换 Rhino 文档；此方案仅关联原文档。");
        });

    private static Button ButtonFor(string text, bool primary = false) => ChatChrome.Button(text, primary);
    private static Label Note(string text) => new() { Text = text, Wrap = WrapMode.Word, TextColor = ChatTimeline.Muted };

    internal void ShowStatus(string text) {
        status.Text = text;
        status.Visible = text.Length > 0;
    }

    internal void AcceptBoundary(BoundarySelection selected)
    {
        if (running is not null)
        {
            ShowStatus("请先完成或取消当前运行。");
            return;
        }
        var carryDraft = boundary is null && program is not null;
        boundary = selected;
        preview.Boundary = selected;
        preview.Enabled = true;
        if (!carryDraft) program = null;
        confirmed = false;
        RetireDraft();
        loadingEntrance = true;
        try
        {
            entrance.Items.Clear();
            for (var edge = 0; edge < selected.Ring.Length - 1; edge++)
                entrance.Items.Add(new ListItem { Text = $"第 {edge + 1} 边 · {selected.EdgeLength(edge):0.##} m" });
            entrance.SelectedIndex = selected.SuggestedEdge;
            preview.Edge = entrance.SelectedIndex;
        }
        finally { loadingEntrance = false; }
        boundaryLabel.Text = $"闭合边界 · {selected.Ring.Length - 1} 条边 · {selected.Area:0.##} m²\n默认入口选最长边，可修改。";
        ClearPlan();
        options.Visible = true;
        ShowStatus(carryDraft ? "已沿用任务书清单。请核对入口边和清单，再生成平面。" : "边界已读取。请核对入口边，可添加任务书或使用简单设计。");
        if (carryDraft) ShowDraftCard();
        UpdateButtons();
    }

    private void LoadExample()
    {
        var doc = RhinoDoc.ActiveDoc ?? throw new InvalidOperationException("请先新建或打开 Rhino 文档。");
        using var document = JsonDocument.Parse(BackendClient.ExampleText());
        var source = document.RootElement;
        var sampleProgram = JsonNode.Parse(source.GetProperty("program").GetRawText())!.AsObject();
        AcceptBoundary(BoundarySelection.FromExample(doc, source));
        briefText = attachmentName = "";
        program = sampleProgram;
        confirmed = true;
        if (source.Value("entrance_edge").TryGetInt32(out var edge))
            entrance.SelectedIndex = edge;
        var bounds = new BoundingBox(boundary!.Ring.Select(boundary.ToModel));
        bounds.Inflate(1 / boundary.MetresPerUnit);
        doc.Views.ActiveView?.ActiveViewport.ZoomBoundingBox(bounds);
        doc.Views.Redraw();
        ShowStatus("已载入内置演示边界和预设清单，未写入文档。");
        UpdateButtons();
    }

    private void Configure()
    {
        using var dialog = new SelectFolderDialog { Title = "选择 thesis-writing 项目根目录", Directory = BackendClient.FindRoot() };
        if (dialog.ShowDialog(composer) != DialogResult.Ok)
            return;
        if (dialog.Directory is not { } directory || !BackendClient.IsRoot(directory))
            throw new InvalidOperationException("此目录不是包含平面生成后端的项目根目录。");
        BackendClient.SetRoot(directory);
        ConnectRefresh();
        ShowStatus("项目目录已设置。");
    }

    private Task ImportBriefAsync(string path)
    {
        return ExecuteAsync("extract", new { path, report_progress = true }, false, message =>
        {
            SetBrief(message.String("brief") ?? "", Path.GetFileName(path));
            chat.Say("任务书已在本机提取。点击「添加任务书」可查看文字，发送“读取任务书，拟定房间清单”可先整理草稿。");
        });
    }

    private Task ProposeAsync(string requestText)
    {
        if (boundary is null && briefText.Trim().Length == 0)
            return Task.CompletedTask;
        return SafelyAsync(() =>
        {
            boundary?.VerifyDocument(RhinoDoc.ActiveDoc);
            var taskText = briefText.Trim();
            if (taskText.Length > 16000)
                throw new InvalidOperationException("任务书文字超过 16,000 字，请先缩减到与本区域相关的内容。");
            var data = taskText.Length == 0 ? "发送这条消息及边界尺寸和形状摘要。"
                : boundary is null ? "发送这条消息和已核对的任务书文字。" : "发送这条消息、已核对的任务书文字及边界摘要。";
            if (!Authorize(data))
                return Task.CompletedTask;
            var request = new { boundary = boundary?.Ring, entrance_edge = entrance.SelectedIndex, brief = taskText,
                message = requestText };
            return ExecuteAsync("propose", request, true, message =>
            {
                ClearPlan();
                program = JsonNode.Parse(message.Value("draft").GetRawText())!.AsObject();
                confirmed = false;
                chat.Say(taskText.Length == 0 ? "已按边界拟定一版清单。这些是建议，不是已确认的建筑要求。"
                    : "已提取任务书要求。请核对清单和缺失信息，再开始生成。");
                ShowDraftCard();
            });
        });
    }

    private bool Authorize(string data) => MessageBox.Show(composer,
        $"{data}\n不会发送原始文件、完整边界坐标或模型权重。继续调用 API 易？",
        "确认发送给外部 API", MessageBoxButtons.YesNo, MessageBoxType.Question, MessageBoxDefaultButton.No) == DialogResult.Yes;

    private void EditProgram()
    {
        using var dialog = new ProgramEditor(program, BackendClient.RoomTypes());
        var edited = dialog.ShowModal(composer);
        if (edited is null)
            return;
        program = edited;
        confirmed = true;
        RetireDraft();
        ClearPlan();
        chat.Say(boundary is null ? "空间清单已核对。请选择建筑外边界，再生成平面。" : "空间清单已确认。可以发送「生成平面」。");
        ShowStatus("清单已确认。");
        UpdateButtons();
    }

    private Task GenerateAsync() => SafelyAsync(() =>
    {
        if (boundary is null || program is null || !confirmed)
            return Task.CompletedTask;
        boundary.VerifyDocument(RhinoDoc.ActiveDoc);
        var allowApi = useAdvice.Checked == true;
        if (allowApi && !Authorize("发送边界摘要、匿名房间类型和允许的候选关系分数。"))
            return Task.CompletedTask;
        ClearPlan();
        chat.Say("开始生成。通过质检后会在 Rhino 视口显示预览；不会自动写入文档。");
        trackLocalPreview = !allowApi;
        var selectedBoundary = boundary;
        var request = new { boundary = selectedBoundary.Ring, entrance_edge = entrance.SelectedIndex, program };
        return ExecuteAsync("run", request, allowApi, message =>
        {
            report = message.Value("report").Clone();
            if (report.String("status") != "completed")
            {
                ShowResultCard(false);
                ShowStatus("未找到通过质检的平面，未改动 Rhino 文档。");
                return;
            }
            selectedBoundary.VerifyDocument(RhinoDoc.ActiveDoc);
            plan = new RhinoPlan(selectedBoundary, report);
            preview.Plan = plan;
            preview.Enabled = true;
            ShowResultCard(true);
            ShowStatus("预览已生成");
            RhinoDoc.ActiveDoc?.Views.Redraw();
        });
    });

    private async Task ExecuteAsync(string operation, object input, bool allowApi, Action<JsonElement> finish,
        Action<string>? appendText = null)
    {
        if (running is not null)
            return;
        using var cancellation = new CancellationTokenSource();
        running = cancellation;
        var version = ++revision;
        UpdateButtons();
        var ordinaryQuestion = operation == "conversation";
        ShowStatus(ordinaryQuestion ? "" : "正在运行，可取消。");
        AgentProgressCard? progress = null;
        Action? dismissThinking = null;
        void EndThinking()
        {
            dismissThinking?.Invoke();
            dismissThinking = null;
        }
        try
        {
            if (ordinaryQuestion)
                dismissThinking = chat.ShowThinking();
            else
            {
                var initial = operation switch
                {
                    "chat" => "正在分析空间清单",
                    "extract" => "正在读取任务书",
                    "propose" => "正在拟定空间清单",
                    _ => "正在准备平面生成"
                };
                latestProgress?.Archive();
                progress = new AgentProgressCard(initial);
                latestProgress = progress;
                chat.Add(progress);
            }
            var result = await backend.InvokeAsync(operation, input, allowApi, item =>
            {
                if (version != revision || cancellation.IsCancellationRequested)
                    return;
                if (item.String("kind") == "text_delta" && item.String("text") is { } chunk)
                {
                    EndThinking();
                    progress?.ReceivingReply();
                    appendText?.Invoke(chunk);
                }
                else if (item.String("kind") == "stage")
                    progress?.UpdateStage(item, operation == "run" && confirmed);
            }, cancellation.Token);
            cancellation.Token.ThrowIfCancellationRequested();
            EndThinking();
            ShowStatus("");
            finish(result);
            progress?.Finish(operation switch
            {
                "run" when result.String("status") == "completed" => "方案审查已完成",
                "run" => "平面生成未通过质检",
                "propose" => "空间清单待确认",
                "extract" => "任务书已读取",
                "chat" => "空间清单处理完成",
                _ => "设计任务完成"
            });
        }
        catch (OperationCanceledException)
        {
            trackLocalPreview = false;
            revision++;
            ShowStatus("运行已取消，未写入 Rhino 文档。");
            progress?.Finish("已取消", "abort");
            chat.Say("已停止这次运行，没有写入 Rhino。");
        }
        catch (Exception error)
        {
            revision++;
            ShowStatus($"运行失败：{error.Message}");
            progress?.Finish("运行失败", "error", error.Message);
            chat.Say($"这一步没有完成：{error.Message}");
        }
        finally
        {
            EndThinking();
            running = null;
            UpdateButtons();
        }
    }

    private void WritePlan()
    {
        if (plan is null || boundary is null || written)
            return;
        var document = RhinoDoc.ActiveDoc;
        boundary.VerifyDocument(document);
        int count = plan.Write(document!);
        written = true;
        preview.Plan = null;
        document!.Views.Redraw();
        if (resultState is not null)
            resultState.Text = $"已写入 {count} 个对象，可一次撤销。";
        ShowStatus($"已写入 {count} 个对象，可用 Rhino Undo 一次撤销。");
        UpdateButtons();
    }

    private void ExportReport()
    {
        if (report.ValueKind != JsonValueKind.Object)
            return;
        using var dialog = new SaveFileDialog { Title = "导出医院首层平面与评估报告", FileName = "医院首层平面报告.json" };
        dialog.Filters.Add(new FileFilter("JSON 报告", ".json"));
        if (dialog.ShowDialog(composer) != DialogResult.Ok)
            return;
        var options = new JsonSerializerOptions { WriteIndented = true, Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
        File.WriteAllText(dialog.FileName, JsonSerializer.Serialize(report, options), new UTF8Encoding(false));
        ShowStatus($"报告已保存：{dialog.FileName}");
    }

    private void ClearPlan()
    {
        trackLocalPreview = false;
        RetireResult();
        plan = null;
        preview.Plan = null;
        report = default;
        written = false;
        RhinoDoc.ActiveDoc?.Views.Redraw();
        UpdateButtons();
    }

    private void UpdateButtons()
    {
        var idle = running is null;
        attachBrief.Enabled = selectBoundary.Enabled = simpleDesign.Enabled = idle;
        var current = boundary is not null && boundary.Document == RhinoDoc.ActiveDoc?.RuntimeSerialNumber;
        add.Enabled = select.Enabled = demo.Enabled = configure.Enabled = openBrief.Enabled = useAdvice.Enabled = idle;
        editProgram.Enabled = entrance.Enabled = idle && current;
        UpdateComposerAction();
        if (resultWrite is not null)
            resultWrite.Enabled = idle && current && plan is not null && !written;
        if (resultExport is not null)
            resultExport.Enabled = idle && report.ValueKind == JsonValueKind.Object;
        if (draftEdit is not null)
            draftEdit.Enabled = idle && (current || boundary is null);
        if (draftGenerate is not null)
            draftGenerate.Enabled = idle && current;
        settings.Visible = editProgram.Visible = current;
        if (!current) options.Visible = false;
        editProgram.Text = program is null ? "手工录入清单" : "编辑清单";
        select.Text = current ? "重新选择边界" : "选择边界";
        openBrief.Text = briefText.Length == 0 ? "附加任务书" : $"查看任务书 · {attachmentName}";
        var rooms = (program?["rooms"] as JsonArray)?.Count ?? 0;
        programLabel.Text = rooms == 0 ? "尚未确认空间清单。" : $"{rooms} 间房 · {(confirmed ? "已确认" : "待确认")}";
    }

    private void UpdateComposerAction()
    {
        var enabled = running is null ? !string.IsNullOrWhiteSpace(composer.Text) : !running.IsCancellationRequested;
        ChatChrome.SetComposerAction(composerAction, running is not null, enabled);
    }

    private void Safely(Action action)
    {
        try { action(); }
        catch (Exception error) { ShowStatus(error.Message); }
    }

    private Task SafelyAsync(Func<Task> action)
    {
        try { return action(); }
        catch (Exception error)
        {
            ShowStatus(error.Message);
            return Task.CompletedTask;
        }
    }
}
