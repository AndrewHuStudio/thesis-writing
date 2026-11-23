using Eto.Drawing;
using Eto.Forms;
using DependencyObject = System.Windows.DependencyObject;
using FrameworkElement = System.Windows.FrameworkElement;
using Media = System.Windows.Media;
using ScrollContentPresenter = System.Windows.Controls.ScrollContentPresenter;
using ScrollViewer = System.Windows.Controls.ScrollViewer;
using VisualTreeHelper = System.Windows.Media.VisualTreeHelper;

namespace OutpatientRhino;

internal sealed class ChatTimeline : Scrollable
{
    private readonly StackLayout messages = new()
    {
        Spacing = 10, Padding = new Padding(8, 5, 8, 10),
        HorizontalContentAlignment = HorizontalAlignment.Stretch
    };
    private readonly List<(FrameworkElement Surface, int Indent)> bubbles = [];

    internal static readonly Color Ink = Color.FromArgb(30, 30, 30);
    internal static readonly Color Muted = Color.FromArgb(76, 76, 76);
    private static readonly Color UserSurface = Color.FromArgb(231, 245, 235);
    private static readonly Color AssistantSurface = Color.FromArgb(248, 248, 248);
    private static readonly Color CardSurface = Color.FromArgb(246, 246, 246);
    private static readonly Color ResultSurface = Color.FromArgb(239, 239, 239);

    internal ChatTimeline()
    {
        Border = BorderType.None;
        BackgroundColor = Colors.White;
        ExpandContentWidth = true;
        MinimumSize = new Size(140, 96);
        Content = messages;
        if (ControlObject is FrameworkElement root)
            root.Loaded += (_, _) => ConfigureScrolling();
        SizeChanged += (_, _) =>
        {
            foreach (var bubble in bubbles)
                bubble.Surface.MaxWidth = BubbleWidth(bubble.Indent);
        };
    }

    private void ConfigureScrolling()
    {
        if (NativeViewer is not { } viewer)
            return;
        viewer.HorizontalScrollBarVisibility = System.Windows.Controls.ScrollBarVisibility.Disabled;
        viewer.VerticalScrollBarVisibility = System.Windows.Controls.ScrollBarVisibility.Auto;
        viewer.ApplyTemplate();
        if (viewer.Template?.FindName("PART_VerticalScrollBar", viewer) is System.Windows.Controls.Primitives.ScrollBar bar)
        {
            bar.Width = 12;
            bar.MinWidth = 0;
            bar.Template = ChatChrome.ScrollBarTemplate;
        }
        viewer.ScrollChanged -= UpdateTopFade;
        viewer.ScrollChanged += UpdateTopFade;
        ApplyTopFade(viewer);
    }

    private static void UpdateTopFade(object sender, System.Windows.Controls.ScrollChangedEventArgs args)
    {
        if (sender is ScrollViewer viewer && args.OriginalSource == viewer)
            ApplyTopFade(viewer);
    }

    private static void ApplyTopFade(ScrollViewer viewer)
    {
        if (viewer.Template?.FindName("PART_ScrollContentPresenter", viewer) is not ScrollContentPresenter viewport)
            return;
        var depth = Math.Min(14, viewer.ContentVerticalOffset);
        if (depth <= 0)
        {
            viewport.OpacityMask = null;
            return;
        }
        var end = new System.Windows.Point(0, depth);
        if (viewport.OpacityMask is Media.LinearGradientBrush previous && previous.EndPoint == end)
            return;
        var fade = new Media.LinearGradientBrush(Media.Color.FromArgb(128, 0, 0, 0), Media.Colors.Black,
            new System.Windows.Point(0, 0), end) { MappingMode = Media.BrushMappingMode.Absolute };
        fade.Freeze();
        viewport.OpacityMask = fade;
    }

    internal void Say(string text, bool user = false)
    {
        var label = AddBubble(user);
        var breaks = System.Globalization.StringInfo.ParseCombiningCharacters(text);
        if (user || breaks.Length <= 3 || ControlObject is not FrameworkElement { IsLoaded: true })
        {
            label.Text = text;
            return;
        }
        var count = 3;
        label.Text = text[..breaks[count]];
        var timer = new UITimer { Interval = 0.035 };
        timer.Elapsed += (_, _) =>
        {
            count += Math.Max(3, breaks.Length / 30);
            if (count >= breaks.Length || ControlObject is not FrameworkElement { IsLoaded: true })
            {
                timer.Stop();
                timer.Dispose();
                UpdateReply(label, text);
                return;
            }
            UpdateReply(label, text[..breaks[count]]);
        };
        timer.Start();
    }

    internal void UpdateReply(Label label, string text)
    {
        var follow = NativeViewer is { } viewer && viewer.ScrollableHeight - viewer.VerticalOffset < 4;
        label.Text = text;
        if (follow)
            Bottom();
    }

    internal MarkdownReply AddMarkdownReply()
    {
        var reply = new MarkdownReply(change =>
        {
            var viewer = NativeViewer;
            var follow = viewer != null && viewer.ScrollableHeight - viewer.VerticalOffset < 4;
            change();
            if (follow) Bottom();
        }, delta =>
        {
            if (NativeViewer is { } viewer) viewer.ScrollToVerticalOffset(viewer.VerticalOffset + delta);
        });
        Add(reply);
        return reply;
    }

    internal void ReleaseReplies()
    {
        foreach (var row in messages.Items)
            if (row.Control is MarkdownReply reply) reply.Dispose();
    }

    private Label AddBubble(bool user = false)
    {
        var row = new StackLayout
        {
            Padding = user ? new Padding(32, 0, 0, 0) : new Padding(0, 0, 16, 0),
            Spacing = 3,
            HorizontalContentAlignment = user ? HorizontalAlignment.Right : HorizontalAlignment.Left
        };
        var label = Text("");
        var bubble = ChatChrome.Rounded(label, user ? UserSurface : AssistantSurface, new Padding(10, 7), 12);
        var indent = user ? 32 : 16;
        if (bubble.ControlObject is FrameworkElement surface)
        {
            surface.MaxWidth = BubbleWidth(indent);
            bubbles.Add((surface, indent));
        }
        row.Items.Add(bubble);
        Add(row);
        return label;
    }

    private double BubbleWidth(int indent) => Math.Clamp(Width > 0 ? Width - indent - 36 : 190, 84, 460);

    internal void Welcome(Button attach, Button selectBoundary, Button simpleDesign)
    {
        var avatar = new ImageView
        {
            Image = Bitmap.FromResource("OutpatientRhino.Welcome.png", typeof(ChatTimeline).Assembly),
            Size = new Size(48, 48)
        };
        var copy = ChatLayout.Column(5);
        var title = Text("一起设计医院首层平面吧");
        title.Font = new Font(SystemFont.Bold, 13);
        copy.Items.Add(title);
        copy.Items.Add(Text("可以直接提问，也可以从任务书或建筑边界开始。想先看看效果，点「做一个简单平面设计」。", muted: true));
        var actions = new StackLayout { Spacing = 4, Items = { attach, selectBoundary, simpleDesign } };
        copy.Items.Add(actions);
        SizeChanged += (_, _) => actions.Orientation = Width >= 580 ? Orientation.Horizontal : Orientation.Vertical;
        var icon = new StackLayout { Items = { avatar } };
        var row = ChatLayout.Row(icon, new TableCell(copy, true));
        if (ControlObject is FrameworkElement chat && avatar.ControlObject is FrameworkElement image)
            welcomeVisibility = WelcomeEntrance.OnShow(chat, image);
        Add(ChatChrome.Rounded(row, AssistantSurface, new Padding(12, 13), 12));
    }

    private Action<bool>? welcomeVisibility;
    internal void SetPanelVisible(bool visible) => welcomeVisibility?.Invoke(visible);

    internal void Card(Control content, bool result = false) =>
        Add(ChatChrome.Rounded(content, result ? ResultSurface : CardSurface, new Padding(11, 8), 10));

    internal void Bottom() => Application.Instance.AsyncInvoke(() =>
    {
        if (ControlObject is FrameworkElement surface)
            surface.UpdateLayout();
        if (NativeViewer is { } viewer)
        {
            viewer.ScrollToBottom();
            return;
        }
        var height = Math.Max(0, Math.Max(messages.Height, ScrollSize.Height) - Height);
        ScrollPosition = new Point(0, height);
    });

    private ScrollViewer? NativeViewer => ControlObject is DependencyObject root ? FindViewer(root, 0) : null;

    private static ScrollViewer? FindViewer(DependencyObject node, int depth)
    {
        if (node is ScrollViewer viewer)
            return viewer;
        if (depth >= 5)
            return null;
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(node); index++)
            if (FindViewer(VisualTreeHelper.GetChild(node, index), depth + 1) is { } found)
                return found;
        return null;
    }

    internal void Add(Control content)
    {
        messages.Items.Add(content);
        Bottom();
    }

    internal Action ShowThinking()
    {
        var text = new ThinkingIndicator();
        var row = new StackLayoutItem(text);
        messages.Items.Add(row);
        Bottom();
        return () =>
        {
            messages.Items.Remove(row);
            text.Dispose();
        };
    }

    internal static Label Text(string value, bool muted = false) => new()
    {
        Text = value, Wrap = WrapMode.Word, TextColor = muted ? Muted : Ink
    };
}

internal static class ChatLayout
{
    internal static StackLayout Column(int spacing = 6, int padding = 0) => new()
    {
        Orientation = Orientation.Vertical, Spacing = spacing, Padding = new Padding(padding),
        HorizontalContentAlignment = HorizontalAlignment.Stretch
    };

    internal static TableLayout Row(params TableCell[] cells) => new()
    {
        Spacing = new Size(6, 0),
        Rows = { new TableRow(cells) }
    };
}
