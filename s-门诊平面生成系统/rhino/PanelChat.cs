using System.Text.Json.Nodes;
using Eto.Drawing;
using Eto.Forms;
using Rhino;

namespace OutpatientRhino;

public sealed partial class OutpatientPanel
{
    private readonly Button attachBrief = ButtonFor("添加任务书");
    private readonly Button selectBoundary = ButtonFor("选择建筑外边界");
    private readonly Button simpleDesign = ButtonFor("做一个简单平面设计");

    private Control CreateChatPanel()
    {
        var layout = ChatLayout.Column(padding: 9);
        layout.BackgroundColor = Colors.White;
        pin.Click += (_, _) => Safely(TogglePin);
        layout.Items.Add(new StackLayoutItem(pin, HorizontalAlignment.Right));
        options.Visible = false;
        settings.Click += (_, _) => options.Visible = !options.Visible;
        var menu = new ContextMenu { Items = { select, openBrief, demo, editProgram, settings, configure } };
        add.ToolTip = "选择边界、附加任务书或查看更多操作";
        add.Click += (_, _) => menu.Show(add);
        options.Items.Add(boundaryLabel);
        options.Items.Add(ChatLayout.Row(ChatTimeline.Text("入口所在边"), new TableCell(entrance, true)));
        options.Items.Add(useAdvice);
        options.Items.Add(showOverlays);
        options.Items.Add(programLabel);
        layout.Items.Add(options);
        layout.Items.Add(new StackLayoutItem(chat, HorizontalAlignment.Stretch, expand: true));
        status.Visible = false;
        layout.Items.Add(status);
        layout.Items.Add(ChatChrome.Composer(composer, add, composerAction));
        composer.ToolTip = "Enter 发送，Shift+Enter 换行";
        attachBrief.Click += async (_, _) => await SafelyAsync(BriefDialogAsync);
        selectBoundary.Click += (_, _) => RhinoApp.RunScript("_OutpatientSelectBoundary", false);
        simpleDesign.Click += async (_, _) => await SafelyAsync(StartSimpleDesignAsync);
        chat.Welcome(attachBrief, selectBoundary, simpleDesign);
        return layout;
    }

    private Task StartSimpleDesignAsync()
    {
        if (boundary is null && program is null && briefText.Length == 0)
            return SubmitAsync("生成示例");
        if (boundary is null || boundary.Document != RhinoDoc.ActiveDoc?.RuntimeSerialNumber)
        {
            chat.Say("已保留当前项目资料。请选择建筑外边界，再生成项目平面。");
            RhinoApp.RunScript("_OutpatientSelectBoundary", false);
            return Task.CompletedTask;
        }
        if (program is null && briefText.Length > 0)
            return ProposeAsync("读取任务书，拟定房间清单");
        if (program is null)
        {
            program = JsonNode.Parse(BackendClient.ExampleText())!["program"]!.AsObject();
            confirmed = false;
            chat.Say("已沿用你的建筑边界。下面是示例的四间房及通行要求，请核对后生成。");
        }
        return ContinueGenerationAsync();
    }

    private async Task SendFromComposerAsync()
    {
        if (running is not null)
        {
            if (!string.IsNullOrWhiteSpace(composer.Text))
                ShowStatus("草稿已保留。当前任务结束后，按 Enter 发送。");
            return;
        }
        var text = (composer.Text ?? "").Trim();
        if (text.Length == 0)
            return;
        if (text.Length > 2000)
        {
            ShowStatus("单条消息最多 2,000 字。较长的任务说明请附为任务书。");
            return;
        }
        composer.Text = "";
        await SubmitAsync(text);
    }

    private async Task SubmitAsync(string text)
    {
        if (running is not null)
            return;
        chat.Say(text, user: true);
        var command = new string(text.Where(character => !char.IsWhiteSpace(character)).ToArray())
            .TrimEnd('。', '！', '？', '.', '!', '?').ToLowerInvariant();
        if (command is "生成一个l形示例" or "生成示例" or "试用l形示例")
        {
            await SafelyAsync(() =>
            {
                LoadExample();
                chat.Say("已载入内置边界与四间房的演示清单，这次不发送任务书。");
                return GenerateAsync();
            });
            return;
        }
        if (command is "写入rhino" or "写入模型" or "导出报告" or "保存报告")
        {
            chat.Say(report.ValueKind == System.Text.Json.JsonValueKind.Object
                ? "请使用结果卡上的按钮。聊天消息不会自动写入 Rhino，也不会覆盖文件。"
                : "目前没有可导出的结果。先生成平面预览。");
            return;
        }
        var edit = command is "确认清单" or "编辑清单" or "手工录入";
        var propose = command is "重新拟定清单" or "重新开始" or "拟定清单" or "读取任务书，拟定房间清单";
        var generate = command is "生成" or "开始生成" or "生成平面" or "生成平面预览" or "再生成" or "生成看看"
            or "再生成看看" or "按当前清单生成" or "按这个清单生成";
        if (!edit && !propose && !generate)
        {
            var action = await ConverseAsync(text);
            if (action is not ("project" or "propose"))
                return;
            propose = action == "propose";
        }
        if (boundary is null || boundary.Document != RhinoDoc.ActiveDoc?.RuntimeSerialNumber)
        {
            if (boundary is null && propose && briefText.Length > 0)
            {
                await ProposeAsync(text);
                return;
            }
            if (boundary is null && edit && program is not null)
            {
                Safely(EditProgram);
                return;
            }
            chat.Say("点击「选择建筑外边界」，再到 Rhino 里选择一条闭合折线。");
            return;
        }
        if (edit)
            Safely(EditProgram);
        else if (propose || program is null)
            await ProposeAsync(text);
        else if (generate)
            await ContinueGenerationAsync();
        else
            await AskForRevisionAsync(text);
    }

    private readonly Queue<Dictionary<string, string>> conversationHistory = new();

    private async Task<string?> ConverseAsync(string text)
    {
        string? action = null;
        MarkdownReply? reply = null;
        var received = new System.Text.StringBuilder();
        await ExecuteAsync("conversation", new { message = text, history = conversationHistory.ToArray() }, true, result =>
        {
            action = result.String("action");
            if (action != "message" || result.String("message") is not { } answer)
                return;
            (reply ??= chat.AddMarkdownReply()).Update(answer, true);
            conversationHistory.Enqueue(new() { ["user"] = text, ["assistant"] = answer[..Math.Min(2000, answer.Length)] });
            if (conversationHistory.Count > 6)
                conversationHistory.Dequeue();
        }, chunk =>
        {
            reply ??= chat.AddMarkdownReply();
            received.Append(chunk);
            reply.Update(received.ToString(), false);
        });
        reply?.Finish();
        return action;
    }

    private async Task ContinueGenerationAsync()
    {
        if (!confirmed)
        {
            chat.Say("先核对这份清单。确认后可直接生成平面。");
            ShowDraftCard();
            return;
        }
        await GenerateAsync();
    }

    private async Task AskForRevisionAsync(string text)
    {
        var generateAfterInterpretation = false;
        MarkdownReply? reply = null;
        await SafelyAsync(() =>
        {
            boundary!.VerifyDocument(RhinoDoc.ActiveDoc);
            if (!Authorize("发送这条消息、边界摘要与当前房间清单的名称、类型和面积范围。不会发送任务书正文。"))
                return Task.CompletedTask;
            var request = new { boundary = boundary.Ring, entrance_edge = entrance.SelectedIndex, program, message = text };
            var received = new System.Text.StringBuilder();
            return ExecuteAsync("chat", request, true, result =>
            {
                var action = result.String("action");
                if (action == "generate")
                {
                    generateAfterInterpretation = true;
                    return;
                }
                var message = result.String("message") ?? "这次没有修改方案。";
                (reply ??= chat.AddMarkdownReply()).Update(message, true);
                if (action != "revision")
                    return;
                ClearPlan();
                program = JsonNode.Parse(result.Value("draft").GetRawText())!.AsObject();
                confirmed = false;
                ShowDraftCard();
                ShowStatus("对话修改已形成草稿。");
            }, chunk =>
            {
                reply ??= chat.AddMarkdownReply();
                received.Append(chunk);
                reply.Update(received.ToString(), false);
            });
        });
        reply?.Finish();
        if (generateAfterInterpretation)
            await ContinueGenerationAsync();
    }

    private async Task BriefDialogAsync()
    {
        using var dialog = new Dialog<int> { Title = "添加任务书", ClientSize = new Size(480, 380), Padding = new Padding(16) };
        var field = new TextArea { Text = briefText, Wrap = true };
        string? selectedPath = null;
        var upload = new BriefUpload(path => { selectedPath = path; dialog.Close(2); });
        var remove = ButtonFor("移除附件");
        remove.Visible = attachmentName.Length > 0;
        var keep = ButtonFor("使用这份文字");
        var close = ButtonFor("取消");
        var layout = ChatLayout.Column(7);
        layout.Items.Add(upload);
        layout.Items.Add(ChatTimeline.Text(attachmentName.Length > 0 ? $"当前附件：{attachmentName}，也可以在下方修改文字。" : "也可以直接粘贴任务书文字", muted: true));
        layout.Items.Add(new StackLayoutItem(field, HorizontalAlignment.Stretch, expand: true));
        layout.Items.Add(ChatLayout.Row(remove, new TableCell(null, true), close, keep));
        remove.Click += (_, _) => dialog.Close(3);
        keep.Click += (_, _) => dialog.Close(1);
        close.Click += (_, _) => dialog.Close(0);
        dialog.AbortButton = close;
        dialog.Content = layout;
        var answer = dialog.ShowModal(composer);
        if (answer == 2 && selectedPath is not null)
            await ImportBriefAsync(selectedPath);
        else if (answer == 3)
            SetBrief("", "");
        else if (answer == 1)
        {
            SetBrief((field.Text ?? "").Trim(), attachmentName.Length > 0 ? attachmentName : "粘贴的任务书");
            if (briefText.Length > 0)
                chat.Say("已附加任务书文字。可以发送「读取任务书，拟定房间清单」。");
        }
    }

    private void SetBrief(string text, string name)
    {
        if (text != briefText)
        {
            confirmed = false;
            RetireDraft();
            ClearPlan();
        }
        briefText = text;
        attachmentName = name;
        UpdateButtons();
    }
}
