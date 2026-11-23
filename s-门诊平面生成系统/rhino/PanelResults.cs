using System.Text.Json;
using System.Text.Json.Nodes;
using Eto.Drawing;
using Eto.Forms;

namespace OutpatientRhino;

public sealed partial class OutpatientPanel
{
    internal static string Issue(JsonElement issue)
    {
        var name = issue.String("code") switch
        {
            "search_failed" => "当前搜索未找到布局",
            "overlap" => "空间重叠",
            "outside_boundary" => "空间越界",
            "room_area" => "房间面积超出范围",
            "corridor_clearance" => "走廊净宽未通过",
            "missing_connection" => "缺少必连门洞",
            "forbidden_connection" => "出现禁连门洞",
            "unreachable_from_entry" => "入口无法到达",
            var other => other ?? "几何质检未通过"
        };
        var detail = issue.String("detail") ?? issue.String("space") ??
            string.Join(" ↔ ", issue.Items("pair").Select(value => value.GetString()));
        return string.IsNullOrEmpty(detail) ? name : $"{name}：{detail}";
    }

    private void ShowDraftCard()
    {
        if (program is null)
            return;
        RetireDraft();
        var rooms = (program["rooms"] as JsonArray)?.OfType<JsonObject>().ToArray() ?? [];
        var roomLines = rooms.Select(room =>
            $"{room["id"]} {room["name"]} · {(room["min_area_m2"] is null || room["max_area_m2"] is null
                ? "面积待补充" : $"{room["min_area_m2"]}–{room["max_area_m2"]} m²")}");
        var card = ChatLayout.Column(5);
        card.Items.Add(new Label { Text = $"{rooms.Length} 间房 · 清单待确认", TextColor = ChatTimeline.Ink,
            Font = new Font(SystemFont.Bold, 12) });
        card.Items.Add(ChatTimeline.Text(string.Join(Environment.NewLine, roomLines)));
        var sources = rooms.Where(room => !string.IsNullOrWhiteSpace(room["source"]?.ToString()))
            .Select(room => $"{room["id"]} · {room["source"]}").ToArray();
        if (sources.Length > 0)
            card.Items.Add(new Expander { Header = "查看房间要求来源", Content = ChatTimeline.Text(string.Join(Environment.NewLine, sources)) });
        var relations = new List<string>();
        foreach (var (key, label) in new[] { ("required_connections", "必须直连"), ("optional_connections", "允许直连"), ("forbidden_connections", "禁止直连") })
            if (program[key] is JsonArray pairs && pairs.Count > 0)
                relations.Add(label + "：" + string.Join("、", pairs.OfType<JsonArray>().Select(pair => string.Join(" ↔ ", pair))));
        if (relations.Count > 0)
            card.Items.Add(new Expander { Header = "核对连通要求", Content = ChatTimeline.Text(string.Join(Environment.NewLine, relations)) });
        if (program["missing"] is JsonArray { Count: > 0 } missing)
            card.Items.Add(ChatTimeline.Text("待核对：" + string.Join("；", missing.Select(item => item?.ToString())), muted: true));
        draftEdit = ButtonFor("核对清单");
        draftEdit.Click += (_, _) => Safely(EditProgram);
        if (program["corridor_width_m"] is not null && program["door_width_m"] is not null &&
            rooms.All(room => room["min_area_m2"] is not null && room["max_area_m2"] is not null))
        {
            draftGenerate = ButtonFor("确认并生成", primary: true);
            draftGenerate.Click += async (_, _) =>
            {
                confirmed = true;
                RetireDraft();
                chat.Say("已确认这份清单，继续生成预览。");
                await GenerateAsync();
            };
        }
        card.Items.Add(ChatLayout.Row(new TableCell(draftEdit, true), new TableCell(draftGenerate, true)));
        chat.Card(card);
        UpdateButtons();
    }

    private void RetireDraft()
    {
        if (draftEdit is not null)
            draftEdit.Enabled = false;
        if (draftGenerate is not null)
            draftGenerate.Enabled = false;
        draftEdit = draftGenerate = null;
    }

    private void ShowResultCard(bool successful)
    {
        var data = report.Value("evaluation");
        var rooms = data.Number("room_count") ?? 0;
        var reachable = rooms - data.Items("unreachable_rooms").Count();
        var title = successful ? $"{rooms:0} 间房 · 入口可达 {reachable:0}/{rooms:0}" : "本轮未得到可交付的平面";
        var card = ChatLayout.Column(5);
        card.Items.Add(new Label { Text = title, TextColor = ChatTimeline.Ink, Font = new Font(SystemFont.Bold, 12),
            Wrap = WrapMode.Word });
        resultState = ChatTimeline.Text(successful ? "预览已显示，尚未写入 Rhino。" : "未改动 Rhino 文档。可导出报告查看原因。", muted: true);
        card.Items.Add(resultState);
        if (!successful)
        {
            var issues = report.Items("attempts").SelectMany(attempt => attempt.Items("issues")).Select(Issue).Distinct();
            card.Items.Add(ChatTimeline.Text(string.Join(Environment.NewLine, issues)));
        }
        if (successful)
        {
            card.Items.Add(new Expander { Header = "查看评估详情", Content = ChatTimeline.Text(Summarize(data), muted: true) });
            var selectedPlan = plan!;
            var selectedBoundary = boundary!;
            var roomsOnPlan = selectedPlan.Parts.Where(part => part.Group == "房间").ToArray();
            var roomPicker = new DropDown();
            foreach (var room in roomsOnPlan) roomPicker.Items.Add(room.Label);
            roomPicker.SelectedIndex = 0;
            var locate = ButtonFor("定位房间");
            locate.Click += (_, _) => Safely(() =>
            {
                if (plan != selectedPlan || roomPicker.SelectedIndex < 0)
                {
                    ShowStatus("请在当前方案的结果卡上定位房间。");
                    return;
                }
                var doc = Rhino.RhinoDoc.ActiveDoc;
                selectedBoundary.VerifyDocument(doc);
                var box = new Rhino.Geometry.BoundingBox(roomsOnPlan[roomPicker.SelectedIndex].Points);
                box.Inflate(1 / selectedBoundary.MetresPerUnit);
                doc!.Views.ActiveView?.ActiveViewport.ZoomBoundingBox(box);
                doc.Views.Redraw();
            });
            card.Items.Add(new Expander { Header = "在 Rhino 中定位", Content = ChatLayout.Row(new TableCell(roomPicker, true), locate) });
            resultWrite = ButtonFor("写入 Rhino", primary: true);
            resultWrite.Click += (_, _) => Safely(WritePlan);
        }
        resultExport = ButtonFor("导出报告");
        resultExport.Click += (_, _) => Safely(ExportReport);
        card.Items.Add(ChatLayout.Row(new TableCell(resultWrite, true), new TableCell(resultExport, true)));
        chat.Card(card, result: true);
        UpdateButtons();
    }

    private void RetireResult()
    {
        if (resultWrite is not null)
            resultWrite.Enabled = false;
        if (resultExport is not null)
            resultExport.Enabled = false;
        if (resultState is not null && !written)
            resultState.Text = "历史结果，不是当前预览。";
        resultWrite = resultExport = null;
        resultState = null;
    }

    private static string Summarize(JsonElement report)
    {
        var roomCount = report.Number("room_count") ?? 0;
        var unreachable = report.Items("unreachable_rooms").Count();
        var visibility = report.Value("visibility").String("status") switch
        {
            "visible" => "无遮挡",
            "blocked" => "受阻",
            _ => "未评估"
        };
        var shared = report.Value("flow_overlap").Number("shared_length_m");
        return $"1 个方案 · {roomCount:0} 间房 · 入口可达 {roomCount - unreachable:0}/{roomCount:0}\n" +
               $"入口视线：{visibility}；患者路径：{Route("patient_route")}；医护路径：{Route("staff_route")}\n" +
               $"流线共用：{(shared is null ? "未评估" : $"{shared:0.##} m")}。概念评估，不代表建筑规范合规。";

        string Route(string key)
        {
            var route = report.Value(key);
            return route.Number("length_m") is { } metres ? $"{metres:0.##} m"
                : route.String("status") == "unreachable" ? "不可达" : "未评估";
        }
    }
}
