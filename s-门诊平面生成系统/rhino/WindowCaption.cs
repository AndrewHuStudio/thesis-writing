using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using Shape = System.Windows.Shapes.Path;

namespace OutpatientRhino;

// The floating Rhino container draws its tab, gear and close controls on one canvas.
// An adorner places the pin on that strip without moving or replacing Rhino's controls.
internal sealed class WindowCaption : Adorner
{
    internal Button Pin { get; } = new();
    private readonly AdornerLayer layer;

    internal WindowCaption(FrameworkElement root, AdornerLayer layer, Action toggle) : base(root)
    {
        this.layer = layer;
        Configure(Pin);
        Pin.Click += (_, _) => toggle();
        AddVisualChild(Pin);
        layer.Add(this);
    }

    internal void Remove() => layer.Remove(this);
    protected override int VisualChildrenCount => 1;
    protected override Visual GetVisualChild(int index) => Pin;

    protected override Size MeasureOverride(Size available)
    {
        Pin.Measure(new Size(22, 20));
        return AdornedElement.RenderSize;
    }

    protected override Size ArrangeOverride(Size size)
    {
        Pin.Arrange(new Rect(Math.Max(0, size.Width - 62.5), 4, 22, 20));
        return size;
    }

    protected override HitTestResult? HitTestCore(PointHitTestParameters hit) => null;

    internal static void Configure(Button pin)
    {
        pin.Background = Brushes.Transparent;
        pin.BorderThickness = new Thickness(0);
        pin.Padding = new Thickness(0);
        pin.Content = new Shape
        {
            Data = Geometry.Parse("M5,2 L15,2 L13,4 L13,8 L16,11 L16,12 L4,12 L4,11 L7,8 L7,4 Z M10,12 L10,19"),
            Width = 11, Height = 12, Stretch = Stretch.Uniform, StrokeThickness = 1.3
        };
    }

    internal static void SetPin(Button pin, bool active, string hint)
    {
        var shape = (Shape)pin.Content;
        shape.Fill = active ? Brushes.Black : Brushes.Transparent;
        shape.Stroke = active ? Brushes.Black : Brushes.DimGray;
        pin.ToolTip = hint;
        AutomationProperties.SetName(pin, hint);
    }
}
