using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Effects;
using System.Windows.Media.Animation;

namespace OutpatientRhino;

internal sealed class BoundaryPickGlow : Adorner, IDisposable
{
    private readonly AdornerLayer layer;
    private readonly Pen edge = new(new SolidColorBrush(Color.FromRgb(89, 175, 134)), 1.5);

    internal BoundaryPickGlow(FrameworkElement target, AdornerLayer layer) : base(target)
    {
        this.layer = layer;
        IsHitTestVisible = false;
        Focusable = false;
        Effect = new DropShadowEffect { Color = Color.FromRgb(89, 175, 134), BlurRadius = 5, ShadowDepth = 0, Opacity = 0.28 };
        Opacity = 0.45;
        if (SystemParameters.ClientAreaAnimation)
            BeginAnimation(OpacityProperty, new DoubleAnimation(0.32, 0.54, TimeSpan.FromSeconds(1.6))
            {
                AutoReverse = true, RepeatBehavior = RepeatBehavior.Forever,
                EasingFunction = new SineEase { EasingMode = EasingMode.EaseInOut }
            });
        layer.Add(this);
    }

    protected override void OnRender(DrawingContext context)
    {
        var size = AdornedElement.RenderSize;
        if (size.Width > 6 && size.Height > 6)
            context.DrawRoundedRectangle(null, edge, new Rect(3, 3, size.Width - 6, size.Height - 6), 5, 5);
    }

    public void Dispose()
    {
        BeginAnimation(OpacityProperty, null);
        layer.Remove(this);
    }
}

public sealed partial class OutpatientPanel
{
    internal BoundaryPickGlow BeginBoundaryPick()
    {
        var host = CurrentPinHost();
        var floatingContent = host != 0 && host != Rhino.RhinoApp.MainWindowHandle()
            ? (System.Windows.Interop.HwndSource.FromHwnd(host)?.RootVisual as Window)?.Content as FrameworkElement
            : null;
        if (floatingContent is not null && AdornerLayer.GetAdornerLayer(floatingContent) is { } floatingLayer)
            return new BoundaryPickGlow(floatingContent, floatingLayer);

        var panel = (FrameworkElement)ControlObject;
        if (AdornerLayer.GetAdornerLayer(panel) is { } panelLayer)
            return new BoundaryPickGlow(panel, panelLayer);

        // A native dock can host Eto without a window-level WPF adorner layer.
        var border = (Border)panel;
        if (border.Child is not AdornerDecorator decorator)
        {
            var content = border.Child;
            border.Child = null;
            decorator = new AdornerDecorator { Child = content };
            border.Child = decorator;
        }
        return new BoundaryPickGlow((FrameworkElement)decorator.Child, decorator.AdornerLayer);
    }
}
