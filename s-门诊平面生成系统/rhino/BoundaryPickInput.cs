using System.Windows;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using Rhino;
using Rhino.Input.Custom;
using Rhino.UI;

namespace OutpatientRhino;

internal sealed class BoundaryPickInput : MouseCallback, IDisposable
{
    private readonly RhinoDoc doc;
    private readonly FrameworkElement panel;
    private bool cancelling;
    private System.Drawing.Point? down;

    internal BoundaryPickInput(RhinoDoc doc, FrameworkElement panel)
    {
        this.doc = doc;
        this.panel = panel;
        panel.PreviewKeyDown += PanelKeyDown;
        panel.MouseLeftButtonUp += PanelClick;
        Enabled = true;
    }

    private void CancelPick()
    {
        if (cancelling) return;
        cancelling = true;
        GetBaseClass.PostCustomMessage(this);
    }

    private void PanelKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key != Key.Escape) return;
        e.Handled = true;
        CancelPick();
    }

    private void PanelClick(object sender, MouseButtonEventArgs e)
    {
        for (var node = e.OriginalSource as DependencyObject; node != null && node != panel;
             node = node is Visual ? VisualTreeHelper.GetParent(node) : LogicalTreeHelper.GetParent(node))
            if (node is ButtonBase or TextBoxBase or Selector or ScrollBar or Thumb) return;
        CancelPick();
    }

    protected override void OnMouseDown(MouseCallbackEventArgs e)
    {
        down = e.MouseButton == Rhino.UI.MouseButton.Left && e.View.Document == doc ? e.ViewportPoint : null;
    }

    protected override void OnMouseUp(MouseCallbackEventArgs e)
    {
        var start = down;
        down = null;
        if (e.Cancel || e.MouseButton != Rhino.UI.MouseButton.Left || start is null || e.View.Document != doc) return;
        var point = e.ViewportPoint;
        if (Math.Abs(point.X - start.Value.X) >= SystemParameters.MinimumHorizontalDragDistance ||
            Math.Abs(point.Y - start.Value.Y) >= SystemParameters.MinimumVerticalDragDistance) return;
        var viewport = e.View.ActiveViewport;
        using var pick = new PickContext { View = e.View, PickStyle = PickStyle.PointPick };
        if (!viewport.GetFrustumLine(point.X, point.Y, out var line)) return;
        pick.PickLine = line;
        pick.SetPickTransform(viewport.GetPickTransform(point));
        pick.UpdateClippingPlanes();
        var hits = doc.Objects.PickObjects(pick);
        if (hits is { Length: > 0 })
        {
            foreach (var hit in hits) hit.Dispose();
            return;
        }
        e.Cancel = true;
        CancelPick();
    }

    public void Dispose()
    {
        Enabled = false;
        panel.MouseLeftButtonUp -= PanelClick;
        panel.PreviewKeyDown -= PanelKeyDown;
    }
}
