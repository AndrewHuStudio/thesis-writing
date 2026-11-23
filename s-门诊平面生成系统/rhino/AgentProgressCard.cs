using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Eto.Forms;
using Microsoft.Web.WebView2.Wpf;

namespace OutpatientRhino;

internal sealed class AgentProgressCard : Panel
{
    private readonly List<JsonObject> events = [];
    private readonly Uri page = new(Path.Combine(Path.GetDirectoryName(typeof(AgentProgressCard).Assembly.Location)!,
        "ChatProgress", "index.html"));
    private WebView2? browser;
    private readonly Stopwatch elapsed = Stopwatch.StartNew();
    private readonly UITimer timer = new() { Interval = 1 };
    private readonly Button toggle = new();
    private readonly Panel details = new() { Visible = false };
    private bool ready;
    private string title, detail;

    internal AgentProgressCard(string initial)
    {
        title = initial;
        detail = initial + "。";
        if (toggle.ControlObject is System.Windows.Controls.Button button)
        {
            button.Template = (System.Windows.Controls.ControlTemplate)System.Windows.Markup.XamlReader.Parse(
                """<ControlTemplate xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" TargetType="Button"><Border Background="Transparent" Padding="2,2"><ContentPresenter/></Border></ControlTemplate>""");
            button.Foreground = System.Windows.Media.Brushes.DimGray;
            button.Cursor = System.Windows.Input.Cursors.Hand;
            button.MinWidth = 0;
            button.FontSize = 12;
        }
        toggle.Click += (_, _) => SetExpanded(!details.Visible);
        var column = ChatLayout.Column(2);
        column.Items.Add(new StackLayoutItem(toggle, HorizontalAlignment.Left));
        column.Items.Add(details);
        Content = column;
        timer.Elapsed += (_, _) => UpdateTime();
        UpdateTime();
        timer.Start();
    }

    private void UpdateTime()
    {
        var seconds = (long)elapsed.Elapsed.TotalSeconds;
        var duration = seconds < 60 ? $"{seconds} 秒" : $"{seconds / 60} 分钟 {seconds % 60} 秒";
        var phase = events.LastOrDefault()?["stage"]?.ToString() switch
        {
            "task" => "需求分析", "gcn" => "平面拓扑", "generation" => "平面生成", "evaluation" => "方案审查",
            _ => ""
        };
        toggle.Text = $"用时 {duration}  {(title.Length > 0 ? title : phase)}  {(details.Visible ? "⌄" : "›")}";
    }

    private void SetExpanded(bool expanded)
    {
        if (expanded == details.Visible) return;
        details.Visible = expanded;
        if (expanded) Open();
        else
        {
            ReleaseBrowser();
            details.Content = null;
        }
        UpdateTime();
    }

    private void Open()
    {
        var view = new WebView2
        {
            CreationProperties = new CoreWebView2CreationProperties
            {
                UserDataFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "OutpatientRhino", "WebView2")
            }
        };
        browser = view;
        details.Height = 32;
        view.Loaded += Initialize;
        details.Content = new NativeControlHost(view);

        async void Initialize(object sender, System.Windows.RoutedEventArgs args)
        {
            view.Loaded -= Initialize;
            try
            {
                await view.EnsureCoreWebView2Async();
                if (browser != view) return;
                view.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
                view.NavigationStarting += (_, args) => args.Cancel = !Uri.TryCreate(args.Uri, UriKind.Absolute, out var target) || target != page;
                view.NavigationCompleted += (_, args) =>
                {
                    if (!args.IsSuccess && browser == view) Fallback(args.WebErrorStatus.ToString());
                };
                view.WebMessageReceived += (_, args) =>
                {
                    if (browser != view || !Uri.TryCreate(args.Source, UriKind.Absolute, out var source) || source != page) return;
                    using var message = JsonDocument.Parse(args.WebMessageAsJson);
                    if (message.RootElement.TryGetProperty("ready", out var readyFlag))
                    {
                        ready = true;
                        Render();
                    }
                    else if (message.RootElement.TryGetProperty("height", out var height) && height.TryGetInt32(out var value))
                        details.Height = Math.Max(20, value + 2);
                };
                view.Source = page;
            }
            catch (Exception error)
            {
                if (browser == view) Fallback(error.Message);
            }
        }
    }

    private void ReleaseBrowser()
    {
        var old = browser;
        browser = null;
        ready = false;
        old?.Dispose();
    }

    private void Fallback(string reason)
    {
        ReleaseBrowser();
        details.Height = -1;
        details.Content = ChatTimeline.Text(title + " · 进度视图加载失败：" + reason);
    }

    internal void Archive() => SetExpanded(false);

    internal void ReceivingReply()
    {
        if (title == "正在生成回复") return;
        title = "正在生成回复";
        detail += " 已开始接收回复。";
        Render();
    }

    internal void UpdateStage(JsonElement message, bool confirmed)
    {
        var stage = message.String("stage");
        if (stage == null) return;
        var record = new JsonObject { ["stage"] = stage, ["status"] = message.String("status") };
        if (confirmed && record["status"]?.ToString() == "awaiting_confirmation")
            record["status"] = "completed";
        foreach (var key in new[] {"attempt", "tools", "room_count", "score_count", "unreachable_count", "reason",
                                   "rooms", "required", "forbidden", "candidates", "doors", "routes", "unreachable", "connection_checks"})
            if (message.TryGetProperty(key, out var field))
                record[key] = JsonNode.Parse(field.GetRawText());
        if (message.TryGetProperty("issues", out _))
            record["issues"] = JsonSerializer.SerializeToNode(message.Items("issues").Select(OutpatientPanel.Issue));
        events.Add(record);
        title = detail = "";
        UpdateTime();
        Render();
    }

    internal void Finish(string summary, string? failure = null, string? reason = null)
    {
        if (failure != null && events.LastOrDefault() is { } last && last["status"]?.ToString() != "completed")
            events.Add(new JsonObject { ["stage"] = last["stage"]?.ToString(), ["status"] = failure, ["reason"] = reason });
        title = summary;
        if (reason != null) detail = reason;
        elapsed.Stop();
        timer.Stop();
        UpdateTime();
        Render();
    }

    private void Render()
    {
        if (ready)
            browser!.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new {title, detail, events}));
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            timer.Dispose();
            ReleaseBrowser();
        }
        base.Dispose(disposing);
    }
}
