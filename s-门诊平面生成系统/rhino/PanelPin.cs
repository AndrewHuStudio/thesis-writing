using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Documents;
using NativeButton = System.Windows.Controls.Button;
using Eto.Forms;
using Rhino;

namespace OutpatientRhino;

public sealed partial class OutpatientPanel : Rhino.UI.IPanel
{
    private readonly Button pin = new() { Width = 28, Height = 24 };
    private WindowCaption? caption;
    private bool watchingPin;
    private nint pinnedByPanel;
    private bool wasTopmost;
    private readonly System.Windows.Threading.DispatcherTimer pinVisibility = new()
    {
        Interval = TimeSpan.FromMilliseconds(150)
    };
    private FrameworkElement PinElement => (FrameworkElement)ControlObject;

    private nint CurrentPinHost()
    {
        if (PresentationSource.FromVisual(PinElement) is not HwndSource source)
            return 0;
        // The WPF control can live in a child HWND inside Rhino's native container.
        return GetAncestor(source.Handle, 2 /* GA_ROOT, excluding the owner */);
    }

    private void TogglePin()
    {
        var host = CurrentPinHost();
        if (host == 0)
            throw new InvalidOperationException("未找到当前面板窗口。");
        if (pinnedByPanel != 0)
            ReleasePin();
        else
        {
            wasTopmost = IsTopmost(host);
            if (!SetTopmost(host, true))
                throw new Win32Exception(Marshal.GetLastWin32Error());
            pinnedByPanel = host;
            if (host != RhinoApp.MainWindowHandle())
                pinVisibility.Start();
        }
        RefreshPin();
    }

    private void WatchPinHost()
    {
        watchingPin = true;
        pinVisibility.Tick += KeepPinnedWindowVisible;
        WindowCaption.Configure((NativeButton)pin.ControlObject);
        PinElement.Loaded += PinLoaded;
        PresentationSource.AddSourceChangedHandler(PinElement, PinSourceChanged);
        RhinoApp.Closing += RhinoClosing;
        RefreshPin();
    }

    private void StopWatchingPinHost()
    {
        watchingPin = false;
        pinVisibility.Tick -= KeepPinnedWindowVisible;
        RemoveCaption();
        PinElement.Loaded -= PinLoaded;
        PresentationSource.RemoveSourceChangedHandler(PinElement, PinSourceChanged);
        RhinoApp.Closing -= RhinoClosing;
        ReleasePin();
    }

    private void ReleasePin()
    {
        if (pinnedByPanel != 0 && !wasTopmost && IsTopmost(pinnedByPanel))
            SetTopmost(pinnedByPanel, false);
        pinnedByPanel = 0;
        pinVisibility.Stop();
    }

    private static bool OtherAppHasFocus()
    {
        var foreground = GetForegroundWindow();
        if (foreground == 0)
            return false;
        GetWindowThreadProcessId(foreground, out var pid);
        return pid != (uint)Environment.ProcessId;
    }

    private void KeepPinnedWindowVisible(object? sender, EventArgs args)
    {
        var host = pinnedByPanel;
        if (host == 0 || !OtherAppHasFocus() || IsWindowVisible(host) && IsTopmost(host))
            return;
        if (HwndSource.FromHwnd(host)?.RootVisual is not System.Windows.Window window)
        {
            ReleasePin();
            return;
        }
        // Rhino hides floating containers when it deactivates. Restore only this
        // pinned container and leave keyboard focus with the foreground application.
        if (!window.IsVisible)
        {
            var activate = window.ShowActivated;
            window.ShowActivated = false;
            try { window.Show(); }
            finally { window.ShowActivated = activate; }
        }
        SetWindowPos(host, -1, 0, 0, 0, 0, 0x53); // SHOWWINDOW | NOSIZE | NOMOVE | NOACTIVATE
    }

    private void PinSourceChanged(object sender, SourceChangedEventArgs args) => ScheduleRefresh();
    private void PinLoaded(object sender, RoutedEventArgs args) => ScheduleRefresh();
    private void ScheduleRefresh() => PinElement.Dispatcher.InvokeAsync(() =>
    {
        if (watchingPin && PinElement.IsVisible)
            RefreshPin();
    });

    private void RemoveCaption()
    {
        caption?.Remove();
        caption = null;
    }
    private void RhinoClosing(object? sender, EventArgs args) => ReleasePin();

    void Rhino.UI.IPanel.PanelShown(uint serial, Rhino.UI.ShowPanelReason reason)
    {
        ScheduleRefresh();
        chat.SetPanelVisible(true);
    }
    void Rhino.UI.IPanel.PanelHidden(uint serial, Rhino.UI.ShowPanelReason reason)
    {
        chat.SetPanelVisible(false);
        if (reason == Rhino.UI.ShowPanelReason.Hide && !OtherAppHasFocus())
        {
            RemoveCaption();
            ReleasePin();
        }
    }
    void Rhino.UI.IPanel.PanelClosing(uint serial, bool documentClosing)
    {
        chat.SetPanelVisible(false);
        ReleasePin();
    }

    private void RefreshPin()
    {
        var host = CurrentPinHost();
        if (pinnedByPanel != 0 && host != 0 && pinnedByPanel != host)
            ReleasePin();
        var active = pinnedByPanel != 0;
        var target = host == RhinoApp.MainWindowHandle() ? "Rhino 主窗口和设计面板" : "当前设计面板";
        var root = host != 0 && host != RhinoApp.MainWindowHandle()
            ? (HwndSource.FromHwnd(host)?.RootVisual as System.Windows.Window)?.Content as FrameworkElement : null;
        if (caption?.AdornedElement != root)
            RemoveCaption();
        if (caption is null && root is not null && AdornerLayer.GetAdornerLayer(root) is { } layer)
            caption = new WindowCaption(root, layer, () => Safely(TogglePin));
        pin.Visible = caption is null;
        var hint = active ? "取消置顶" : $"置顶{target}";
        WindowCaption.SetPin((NativeButton)pin.ControlObject, active, hint);
        if (caption is not null)
            WindowCaption.SetPin(caption.Pin, active, hint);
    }

    private static bool IsTopmost(nint host) => (GetWindowLong(host, -20) & 0x8) != 0;

    private static bool SetTopmost(nint host, bool active) =>
        SetWindowPos(host, active ? -1 : -2, 0, 0, 0, 0, 0x13); // NOSIZE | NOMOVE | NOACTIVATE

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(nint host);

    [DllImport("user32.dll")]
    private static extern nint GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint window, out uint processId);

    [DllImport("user32.dll")]
    private static extern nint GetAncestor(nint window, uint flags);

    [DllImport("user32.dll", EntryPoint = "GetWindowLongW")]
    private static extern int GetWindowLong(nint window, int index);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool SetWindowPos(nint window, nint after, int x, int y, int width, int height, uint flags);
}
