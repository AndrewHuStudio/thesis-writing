using System.Diagnostics;
using System.Globalization;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Web.WebView2.Wpf;

namespace OutpatientRhino;

internal sealed class MarkdownReply : Eto.Forms.Panel
{
    private static readonly Uri Page = new(Path.Combine(Path.GetDirectoryName(typeof(MarkdownReply).Assembly.Location)!,
        "ChatProgress", "reply.html"));
    private readonly TextBlock fallback = new() { TextWrapping = TextWrapping.Wrap, FontSize = 14, Visibility = Visibility.Collapsed };
    private readonly System.Windows.Threading.DispatcherTimer startupTimeout = new() { Interval = TimeSpan.FromSeconds(4) };
    private readonly WebView2 view = new()
    {
        Height = 24, Visibility = Visibility.Hidden,
        CreationProperties = new CoreWebView2CreationProperties
        {
            UserDataFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "OutpatientRhino", "WebView2")
        }
    };
    private readonly Action<Action> resize;
    private readonly Action<double> scroll;
    private string text = "";
    private bool complete, ready, disposed;

    internal MarkdownReply(Action<Action> resize, Action<double> scroll)
    {
        this.resize = resize;
        this.scroll = scroll;
        var grid = new Grid { MinHeight = 24, ClipToBounds = true, Children = { fallback, view } };
        Content = new Eto.Forms.NativeControlHost(grid);
        startupTimeout.Tick += StartupTimedOut;
        view.Loaded += Initialize;
    }

    internal void Update(string value, bool done)
    {
        if (disposed || (text == value && complete == done)) return;
        var changed = text != value;
        text = value;
        complete = done;
        if (fallback.Visibility == Visibility.Visible && changed)
            resize(() => fallback.Text = value);
        if (ready && changed) Publish();
        else if (ready && done) view.CoreWebView2.PostWebMessageAsJson("""{"done":true}""");
    }

    internal void Finish() => Update(text, true);

    private void Publish() => view.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(new { text, done = complete }));

    private void StartupTimedOut(object? sender, EventArgs args) => UsePlainText();

    private void UsePlainText()
    {
        startupTimeout.Stop();
        if (disposed || fallback.Visibility == Visibility.Visible) return;
        ready = false;
        view.Visibility = Visibility.Collapsed;
        resize(() =>
        {
            fallback.Visibility = Visibility.Visible;
            fallback.Text = text;
        });
    }

    private async void Initialize(object sender, RoutedEventArgs args)
    {
        view.Loaded -= Initialize;
        startupTimeout.Start();
        try
        {
            await view.EnsureCoreWebView2Async();
            if (disposed || fallback.Visibility == Visibility.Visible) return;
            var core = view.CoreWebView2;
            core.NavigationCompleted += (_, e) => { if (!e.IsSuccess) UsePlainText(); };
            core.ProcessFailed += (_, e) =>
            {
                if (e.ProcessFailedKind is Microsoft.Web.WebView2.Core.CoreWebView2ProcessFailedKind.BrowserProcessExited
                    or Microsoft.Web.WebView2.Core.CoreWebView2ProcessFailedKind.RenderProcessExited)
                    UsePlainText();
            };
            core.Settings.IsZoomControlEnabled = false;
            core.Settings.AreDefaultScriptDialogsEnabled = false;
            core.NavigationStarting += (_, e) => e.Cancel = !Uri.TryCreate(e.Uri, UriKind.Absolute, out var uri) || uri != Page;
            core.NewWindowRequested += (_, e) =>
            {
                e.Handled = true;
                if (!e.IsUserInitiated || !Uri.TryCreate(e.Uri, UriKind.Absolute, out var uri) ||
                    uri.Scheme is not ("http" or "https")) return;
                try { Process.Start(new ProcessStartInfo(uri.AbsoluteUri) { UseShellExecute = true }); }
                catch (System.ComponentModel.Win32Exception error) { Trace.WriteLine(error.Message); }
            };
            core.WebMessageReceived += (_, e) =>
            {
                if (disposed || fallback.Visibility == Visibility.Visible || new Uri(e.Source) != Page) return;
                var value = e.TryGetWebMessageAsString();
                if (value == "ready")
                {
                    if (ready) return;
                    startupTimeout.Stop();
                    ready = true;
                    view.Visibility = Visibility.Visible;
                    Publish();
                }
                else if (value.StartsWith("height:") && int.TryParse(value.AsSpan(7), out var height) && height > 4)
                    resize(() =>
                    {
                        view.Height = Math.Max(24, height);
                        view.Visibility = Visibility.Visible;
                    });
                else if (value.StartsWith("scroll:") && double.TryParse(value.AsSpan(7), CultureInfo.InvariantCulture, out var dy) && double.IsFinite(dy))
                    scroll(dy);
            };
            view.Source = Page;
        }
        catch (Exception error)
        {
            Trace.WriteLine($"Markdown reply: {error.Message}");
            UsePlainText();
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing && !disposed)
        {
            disposed = true;
            startupTimeout.Stop();
            startupTimeout.Tick -= StartupTimedOut;
            view.Loaded -= Initialize;
            view.Dispose();
        }
        base.Dispose(disposing);
    }
}
