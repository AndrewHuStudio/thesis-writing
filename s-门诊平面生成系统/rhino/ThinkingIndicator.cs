using NativeControlHost = Eto.Forms.NativeControlHost;
using Microsoft.Web.WebView2.Wpf;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;

namespace OutpatientRhino;

internal sealed class ThinkingIndicator : Eto.Forms.Panel
{
    private readonly WebView2 view = new()
    {
        Focusable = false, IsHitTestVisible = false, Visibility = Visibility.Hidden,
        CreationProperties = new CoreWebView2CreationProperties
        {
            UserDataFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "OutpatientRhino", "WebView2")
        }
    };
    private readonly TranslateTransform sweep = new();
    private bool released;

    internal ThinkingIndicator()
    {
        Height = 24;
        var text = new TextBlock { Text = "正在思考", FontSize = 14, VerticalAlignment = VerticalAlignment.Center,
            HorizontalAlignment = System.Windows.HorizontalAlignment.Left, Foreground = Brushes.DimGray };
        // Paint the first frame immediately, including while WebView2 starts.
        if (SystemParameters.ClientAreaAnimation && !SystemParameters.HighContrast)
        {
            var brush = new LinearGradientBrush { StartPoint = new Point(0, 0), EndPoint = new Point(1, 0),
                RelativeTransform = sweep };
            brush.GradientStops.Add(new(Colors.Gray, 0.27));
            brush.GradientStops.Add(new(Colors.Black, 0.5));
            brush.GradientStops.Add(new(Colors.Gray, 0.73));
            text.Foreground = brush;
            sweep.BeginAnimation(TranslateTransform.XProperty, new DoubleAnimation(-0.65, 0.65,
                TimeSpan.FromSeconds(1.4)) { RepeatBehavior = RepeatBehavior.Forever });
        }
        var grid = new Grid { Children = { text, view } };
        Content = new NativeControlHost(grid);
        view.Loaded += Initialize;
    }

    private async void Initialize(object sender, RoutedEventArgs args)
    {
        view.Loaded -= Initialize;
        var page = new Uri(Path.Combine(Path.GetDirectoryName(typeof(ThinkingIndicator).Assembly.Location)!,
            "ChatProgress", "thinking.html"));
        try
        {
            await view.EnsureCoreWebView2Async();
            if (released) return;
            view.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            view.NavigationStarting += (_, e) => e.Cancel = !Uri.TryCreate(e.Uri, UriKind.Absolute, out var uri) || uri != page;
            view.WebMessageReceived += (_, e) =>
            {
                if (released || new Uri(e.Source) != page || e.TryGetWebMessageAsString() != "ready") return;
                view.Visibility = Visibility.Visible;
                sweep.BeginAnimation(TranslateTransform.XProperty, null);
            };
            view.Source = page;
        }
        catch (Exception error)
        {
            if (!released) System.Diagnostics.Trace.WriteLine($"Thinking indicator: {error.Message}");
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing && !released)
        {
            released = true;
            view.Loaded -= Initialize;
            sweep.BeginAnimation(TranslateTransform.XProperty, null);
            view.Dispose();
        }
        base.Dispose(disposing);
    }
}
