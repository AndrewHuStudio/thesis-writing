using System.Windows;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;

namespace OutpatientRhino;

internal sealed class WelcomeEntrance : Adorner
{
    private static readonly DependencyProperty ProgressProperty = DependencyProperty.Register(
        "Progress", typeof(double), typeof(WelcomeEntrance),
        new FrameworkPropertyMetadata(0d, FrameworkPropertyMetadataOptions.AffectsRender));
    private static readonly BitmapImage Logo = LoadLogo();
    private static readonly TimeSpan Duration = TimeSpan.FromMilliseconds(780);
    private const double LaunchTime = 0.16;
    private const double TurnTime = 0.54;
    private readonly FrameworkElement avatar;
    private readonly AdornerLayer layer;

    private WelcomeEntrance(FrameworkElement chat, FrameworkElement avatar, AdornerLayer layer) : base(chat)
    {
        this.avatar = avatar;
        this.layer = layer;
        IsHitTestVisible = false;
        ClipToBounds = true;
    }

    internal static Action<bool> OnShow(FrameworkElement chat, FrameworkElement avatar)
    {
        WelcomeEntrance? effect = null;
        bool shown = false;
        void Update(bool visible)
        {
            if (!visible)
            {
                shown = false;
                effect?.Finish();
                effect = null;
                return;
            }
            chat.Dispatcher.InvokeAsync(() =>
            {
                if (shown || !chat.IsVisible || !avatar.IsLoaded || avatar.ActualWidth <= 0)
                    return;
                if (SystemParameters.ClientAreaAnimation && AdornerLayer.GetAdornerLayer(chat) is { } layer)
                {
                    shown = true;
                    effect = new WelcomeEntrance(chat, avatar, layer);
                    effect.Play();
                }
            }, System.Windows.Threading.DispatcherPriority.Loaded);
        }
        chat.IsVisibleChanged += (_, _) => Update(chat.IsVisible);
        chat.Loaded += (_, _) => Update(true);
        chat.Unloaded += (_, _) => Update(false);
        return Update;
    }

    private void Play()
    {
        layer.Add(this);
        avatar.Opacity = 0;
        var motion = new DoubleAnimation(0, 1, Duration);
        motion.Completed += (_, _) => Finish();
        BeginAnimation(ProgressProperty, motion);
    }

    private bool finished;
    private void Finish()
    {
        if (finished)
            return;
        finished = true;
        BeginAnimation(ProgressProperty, null);
        avatar.Opacity = 1;
        layer.Remove(this);
    }

    protected override void OnRender(DrawingContext dc)
    {
        var chat = (FrameworkElement)AdornedElement;
        if (!avatar.IsLoaded || !chat.IsAncestorOf(avatar))
            return;
        var t = (double)GetValue(ProgressProperty);
        var end = avatar.TranslatePoint(new Point(avatar.ActualWidth / 2, avatar.ActualHeight / 2), chat);
        // An existing conversation may be scrolled past the welcome card.
        // Land at the same top-left inset without moving the reader's scroll position.
        var offscreen = end.Y < 0 || end.Y > chat.ActualHeight;
        if (offscreen)
            end.Y = Math.Min(chat.ActualHeight / 2, avatar.ActualHeight / 2 + 18);
        var glide = Math.Clamp((t - TurnTime) / (1 - TurnTime), 0, 1);
        var ease = glide * glide * (3 - 2 * glide);
        var openingSize = Math.Min(320, Math.Min(chat.ActualWidth * 0.65, chat.ActualHeight * 0.55));
        var position = Position(t, chat.RenderSize, end, openingSize);
        var size = openingSize + (avatar.ActualWidth - openingSize) * ease;
        dc.PushOpacity(1 - ease);
        dc.DrawRectangle(Brushes.White, null, new Rect(chat.RenderSize));
        dc.Pop();
        var start = Math.Max(0, t - 0.105);
        var tail = Position(start, chat.RenderSize, end, openingSize);
        if ((position - tail).Length > 2)
        {
            var path = new StreamGeometry();
            using (var line = path.Open())
            {
                line.BeginFigure(tail, false, false);
                for (int i = 1; i <= 18; i++)
                    line.LineTo(Position(start + (t - start) * i / 18, chat.RenderSize, end, openingSize), true, true);
            }
            var tint = new LinearGradientBrush(Colors.Transparent, Color.FromArgb(75, 30, 198, 152), tail, position)
                { MappingMode = BrushMappingMode.Absolute };
            dc.PushOpacity(1 - ease);
            dc.DrawGeometry(null, new Pen(tint, size * 0.40) { LineJoin = PenLineJoin.Round }, path);
            dc.Pop();
        }
        var height = size * Logo.PixelHeight / Logo.PixelWidth;
        dc.PushOpacity(offscreen ? Math.Clamp((1 - t) / 0.09, 0, 1) : 1);
        dc.DrawImage(Logo, new Rect(position.X - size / 2, position.Y - height / 2, size, height));
        dc.Pop();
    }

    private static Point Position(double t, Size viewport, Point end, double openingSize)
    {
        var x = viewport.Width / 2;
        var middle = viewport.Height / 2;
        var bottom = Math.Min(viewport.Height * 0.86, viewport.Height - openingSize * 0.5);
        if (t <= TurnTime)
        {
            var fall = Math.Clamp((t - LaunchTime) / (TurnTime - LaunchTime), 0, 1);
            return new Point(x, middle + (bottom - middle) * Math.Pow(fall, 2.4));
        }
        var u = (t - TurnTime) / (1 - TurnTime);
        var v = 1 - u;
        // A downward tangent rounds the turn, then the curve eases into the avatar.
        return new Point(end.X + (x - end.X) * v * v * (1 + 2 * u),
            end.Y + (bottom - end.Y) * v * v * (1 + 2 * u) + 3 * v * v * u * viewport.Height * 0.16);
    }

    private static BitmapImage LoadLogo()
    {
        using var stream = typeof(WelcomeEntrance).Assembly.GetManifestResourceStream("OutpatientRhino.Welcome.png");
        var bitmap = new BitmapImage();
        bitmap.BeginInit();
        bitmap.CacheOption = BitmapCacheOption.OnLoad;
        bitmap.DecodePixelWidth = 640;
        bitmap.StreamSource = stream;
        bitmap.EndInit();
        bitmap.Freeze();
        return bitmap;
    }
}
