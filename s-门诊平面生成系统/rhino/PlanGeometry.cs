using System.Drawing;
using System.Globalization;
using System.Text.Json;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace OutpatientRhino;

internal sealed record BoundarySelection(uint Document, Guid Source, uint SourceCrc, UnitSystem Units,
    Plane Plane, double MetresPerUnit, double[][] Ring, double Area)
{
    internal static double MetreScale(RhinoDoc doc)
    {
        if (doc.ModelUnitSystem is UnitSystem.None or UnitSystem.Unset or UnitSystem.CustomUnits)
            throw new InvalidOperationException("请先在 Rhino 文档中设置明确的长度单位，例如毫米或米。");
        var scale = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Meters);
        if (!double.IsFinite(scale) || scale <= 0)
            throw new InvalidOperationException("无法将当前 Rhino 文档单位换算为米。");
        return scale;
    }

    internal static BoundarySelection FromObject(RhinoDoc doc, ObjRef reference)
    {
        var curve = reference.Curve();
        if (curve is null || !curve.IsClosed || !curve.TryGetPolyline(out var polyline) ||
            polyline.Count is < 4 or > 101 || !curve.TryGetPlane(out var plane, doc.ModelAbsoluteTolerance))
            throw new InvalidOperationException("请选择由 3–100 条直线边组成的单条闭合平面折线。");
        var first = polyline[0];
        plane = polyline.All(point => Math.Abs(point.Z - first.Z) <= doc.ModelAbsoluteTolerance)
            ? new Plane(first, Vector3d.XAxis, Vector3d.YAxis)
            : new Plane(first, plane.XAxis, plane.YAxis);
        var scale = MetreScale(doc);
        var ring = polyline.Select(point =>
        {
            plane.ClosestParameter(point, out var xCoord, out var yCoord);
            return new[] { xCoord * scale, yCoord * scale };
        }).ToArray();
        ring[^1] = ring[0];
        return Create(doc, reference.ObjectId, curve.DataCRC(0), plane, scale, ring);
    }

    internal static BoundarySelection FromExample(RhinoDoc doc, JsonElement example) =>
        Create(doc, Guid.Empty, 0, Plane.WorldXY, MetreScale(doc), example.Items("boundary").Select(Coordinates).ToArray());

    private static BoundarySelection Create(RhinoDoc doc, Guid id, uint crc, Plane plane, double scale, double[][] ring)
    {
        var area = 0.0;
        for (var index = 1; index < ring.Length; index++)
            area += ring[index - 1][0] * ring[index][1] - ring[index][0] * ring[index - 1][1];
        area = Math.Abs(area / 2);
        if (ring.Length < 4 || !double.IsFinite(area) || area < 0.01)
            throw new InvalidOperationException("建筑边界无有效面积，请检查折线、单位或自交。");
        return new BoundarySelection(doc.RuntimeSerialNumber, id, crc, doc.ModelUnitSystem, plane, scale, ring, area);
    }

    internal double EdgeLength(int edge) =>
        Math.Sqrt(Math.Pow(Ring[edge][0] - Ring[edge + 1][0], 2) + Math.Pow(Ring[edge][1] - Ring[edge + 1][1], 2));

    internal int SuggestedEdge => Enumerable.Range(0, Ring.Length - 1).MaxBy(EdgeLength);

    internal Point3d ToModel(IReadOnlyList<double> point) => Plane.PointAt(point[0] / MetresPerUnit, point[1] / MetresPerUnit);

    internal Point3d[] Path(JsonElement array) => array.ValueKind == JsonValueKind.Array
        ? array.EnumerateArray().Select(point => ToModel(Coordinates(point))).ToArray() : [];

    internal static double[] Coordinates(JsonElement element) => element.EnumerateArray().Select(part => part.GetDouble()).ToArray();

    internal void VerifyDocument(RhinoDoc? doc)
    {
        if (doc is null || doc.RuntimeSerialNumber != Document)
            throw new InvalidOperationException("当前 Rhino 文档已切换。请回到原文档，或重新选择边界。");
        if (doc.ModelUnitSystem != Units)
            throw new InvalidOperationException("文档单位已更改。请重新选择边界并生成。");
        if (Source != Guid.Empty && doc.Objects.FindId(Source)?.Geometry.DataCRC(0) != SourceCrc)
            throw new InvalidOperationException("原边界已删除或修改。请重新选择边界并生成。");
    }
}

internal sealed record PlanPart(string Group, string Label, string? RoomId, Point3d[] Points, Color Color)
{
    internal bool Overlay => Group == "流线与视线";
}

internal sealed class RhinoPlan
{
    internal List<PlanPart> Parts { get; } = [];

    internal RhinoPlan(BoundarySelection boundary, JsonElement report)
    {
        var layout = report.Value("layout");
        var evaluation = report.Value("evaluation");
        if (report.String("status") != "completed" || layout.ValueKind != JsonValueKind.Object)
            throw new InvalidOperationException("报告没有通过质检、可预览的平面。");
        var roomInfo = evaluation.Items("rooms").ToDictionary(room => room.String("id") ?? "");
        Add("走廊", "走廊", null, layout.Value("corridor"), Color.SteelBlue);
        foreach (var room in layout.Value("rooms").EnumerateObject())
        {
            var info = roomInfo.GetValueOrDefault(room.Name);
            var area = info.Number("area_m2")?.ToString("0.##", CultureInfo.InvariantCulture);
            var label = $"{room.Name}  {info.String("name")}  {area} m²";
            var points = Add("房间", label, room.Name, room.Value, Color.DodgerBlue);
            var center = new BoundingBox(points).Center;
            Parts.Add(new PlanPart("房间标注", label, room.Name, [center], Color.DodgerBlue));
        }
        foreach (var door in layout.Items("doors"))
            Add("门洞", "门洞", null, door.Value("line"), Color.DarkOrange);
        Add("流线与视线", "患者路线", null, evaluation.Value("patient_route").Value("line"), Color.MediumSeaGreen);
        Add("流线与视线", "医护路线", null, evaluation.Value("staff_route").Value("line"), Color.MediumVioletRed);
        Add("流线与视线", "入口视线", null, evaluation.Value("visibility").Value("line"), Color.DarkOrange);
        if (layout.Value("entry") is { ValueKind: JsonValueKind.Array } entry)
            Parts.Add(new PlanPart("入口标注", "入口", null, [boundary.ToModel(BoundarySelection.Coordinates(entry))], Color.SteelBlue));

        Point3d[] Add(string group, string label, string? roomId, JsonElement source, Color color)
        {
            var points = boundary.Path(source);
            if (points.Length >= 2)
                Parts.Add(new PlanPart(group, label, roomId, points, color));
            return points;
        }
    }

    internal int Write(RhinoDoc doc)
    {
        var undo = doc.BeginUndoRecord("写入医院首层平面");
        if (undo == 0)
            throw new InvalidOperationException("当前 Rhino 命令占用了撤销记录，请退出当前命令后重试。");
        var layers = new List<int>();
        var objects = new List<Guid>();
        try
        {
            var parent = AddLayer($"医院首层方案 {DateTime.Now:yyyyMMdd-HHmmssfff}", Guid.Empty, Color.SteelBlue);
            var groups = new Dictionary<string, int>();
            foreach (var part in Parts)
            {
                if (!groups.TryGetValue(part.Group, out var layer))
                {
                    layer = AddLayer(part.Group, doc.Layers[parent].Id, part.Color);
                    groups[part.Group] = layer;
                }
                var attributes = new ObjectAttributes { LayerIndex = layer, Name = part.Label, ObjectColor = part.Color,
                    ColorSource = ObjectColorSource.ColorFromObject };
                if (part.RoomId is not null)
                    attributes.SetUserString("OutpatientRoomId", part.RoomId);
                var id = part.Points.Length == 1
                    ? doc.Objects.AddTextDot(part.Label, part.Points[0], attributes)
                    : doc.Objects.AddPolyline(part.Points, attributes);
                if (id == Guid.Empty)
                    throw new InvalidOperationException("Rhino 未能写入一项方案几何，已回退本次写入。");
                objects.Add(id);
            }
            return objects.Count;
        }
        catch
        {
            foreach (var id in objects)
                doc.Objects.Delete(id, true);
            foreach (var layer in Enumerable.Reverse(layers))
                doc.Layers.Delete(layer, true);
            throw;
        }
        finally
        {
            doc.EndUndoRecord(undo);
            doc.Views.Redraw();
        }

        int AddLayer(string name, Guid parentId, Color color)
        {
            var layer = new Layer { Name = name, ParentLayerId = parentId, Color = color };
            var index = doc.Layers.Add(layer);
            if (index < 0)
                throw new InvalidOperationException("Rhino 未能创建方案图层。");
            layers.Add(index);
            return index;
        }
    }
}

internal sealed class PlanPreview : DisplayConduit
{
    internal BoundarySelection? Boundary { get; set; }
    internal RhinoPlan? Plan { get; set; }
    internal int Edge { get; set; } = -1;
    internal bool ShowOverlays { get; set; }
    internal bool ShowBoundary { get; set; } = true;

    protected override void PostDrawObjects(DrawEventArgs args)
    {
        var boundary = Boundary;
        if (boundary is null || args.RhinoDoc?.RuntimeSerialNumber != boundary.Document ||
            args.RhinoDoc?.ModelUnitSystem != boundary.Units)
            return;
        if (ShowBoundary)
            args.Display.DrawPolyline(boundary.Ring.Select(boundary.ToModel), Color.Gray, 2);
        if (Edge >= 0 && ShowBoundary)
        {
            var first = boundary.ToModel(boundary.Ring[Edge]);
            var second = boundary.ToModel(boundary.Ring[Edge + 1]);
            var midpoint = (first + second) * 0.5;
            args.Display.DrawPoint(midpoint, PointStyle.Simple, 6, Color.SteelBlue);
        }
        foreach (var part in Plan?.Parts ?? [])
        {
            if (part.Overlay && !ShowOverlays)
                continue;
            if (part.Points.Length == 1)
                args.Display.DrawDot(part.Points[0], part.Label, part.Color, Color.White);
            else
                args.Display.DrawPolyline(part.Points, part.Color, part.Group == "门洞" ? 4 : 2);
        }
    }
}
