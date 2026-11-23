using System.Runtime.InteropServices;
using Rhino;
using Rhino.Commands;
using Rhino.DocObjects;
using Rhino.Input.Custom;
using Rhino.PlugIns;
using Rhino.UI;

[assembly: Guid("0156ac98-6880-4a24-8584-d461fa55fb78")]

namespace OutpatientRhino;

[Guid("0156ac98-6880-4a24-8584-d461fa55fb78")]
public sealed class OutpatientPlugin : PlugIn
{
    internal static OutpatientPlugin? Instance { get; private set; }

    public OutpatientPlugin() => Instance = this;

    protected override LoadReturnCode OnLoad(ref string errorMessage)
    {
        try
        {
            Panels.RegisterPanel(this, typeof(OutpatientPanel), "医院首层平面设计", null, PanelType.System);
            RhinoApp.Idle += InstallToolbar;
            return LoadReturnCode.Success;
        }
        catch (Exception error)
        {
            errorMessage = $"OutpatientRhino: {error.Message}";
            RhinoApp.WriteLine(errorMessage);
            return LoadReturnCode.ErrorShowDialog;
        }
    }

    private void InstallToolbar(object? sender, EventArgs args)
    {
        RhinoApp.Idle -= InstallToolbar;
        try
        {
            const string key = "LauncherToolbarInstalled";
            if (Settings.GetBool(key, false))
                return;
            var path = Path.ChangeExtension(GetType().Assembly.Location, ".rui");
            var files = RhinoApp.ToolbarFiles;
            var toolbar = files.FindByPath(path) ?? files.FindByName("OutpatientRhino", true) ?? files.Open(path);
            if (toolbar is null || toolbar.GroupCount == 0)
                throw new InvalidOperationException($"无法读取工具栏 {path}");
            toolbar.GetGroup(0).Visible = true;
            Settings.SetBool(key, true);
        }
        catch (Exception error)
        {
            RhinoApp.WriteLine($"医院首层平面设计工具栏加载失败：{error.Message}");
        }
    }
}

public sealed class OutpatientPlannerCommand : Command
{
    public override string EnglishName => "OutpatientPlanner";

    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        Panels.OpenPanel(typeof(OutpatientPanel));
        return Result.Success;
    }
}

public sealed class OutpatientSelectBoundaryCommand : Command
{
    public override string EnglishName => "OutpatientSelectBoundary";

    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        Panels.OpenPanel(typeof(OutpatientPanel));
        var panel = Panels.GetPanel<OutpatientPanel>(doc);
        if (panel is null)
            return Result.Failure;
        using var getter = new GetObject();
        getter.SetCommandPrompt("选择闭合平面折线作为建筑边界，按 Esc 或单击空白处取消");
        getter.GeometryFilter = ObjectType.Curve;
        getter.SetCustomGeometryFilter((_, geometry, _) => geometry is Rhino.Geometry.Curve curve &&
            curve.IsClosed && curve.TryGetPolyline(out var polyline) && polyline.Count is >= 4 and <= 101 &&
            curve.TryGetPlane(out _, doc.ModelAbsoluteTolerance));
        getter.SubObjectSelect = false;
        getter.AcceptCustomMessage(true);
        using var glow = panel.BeginBoundaryPick();
        using var input = new BoundaryPickInput(doc, (System.Windows.FrameworkElement)panel.ControlObject);
        if (getter.Get() == Rhino.Input.GetResult.CustomMessage)
            return Result.Cancel;
        if (getter.CommandResult() != Result.Success)
            return getter.CommandResult();
        try
        {
            panel.AcceptBoundary(BoundarySelection.FromObject(doc, getter.Object(0)));
            return Result.Success;
        }
        catch (InvalidOperationException exception)
        {
            panel.ShowStatus(exception.Message);
            RhinoApp.WriteLine(exception.Message);
            return Result.Failure;
        }
    }
}
