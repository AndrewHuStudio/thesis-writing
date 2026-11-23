using System.Globalization;
using System.Text.Json.Nodes;
using Eto.Drawing;
using Eto.Forms;

namespace OutpatientRhino;

internal sealed class ProgramEditor : Dialog<JsonObject?>
{
    private readonly JsonObject original;
    private readonly Dictionary<string, string> roomTypes;
    private readonly List<RoomFields> rooms = [];
    private readonly StackLayout table = new() { Spacing = 5, HorizontalContentAlignment = HorizontalAlignment.Stretch };
    private readonly TextBox corridor;
    private readonly TextBox door;
    private readonly TextBox required;
    private readonly TextBox optional;
    private readonly TextBox forbidden;
    private readonly TextBox sight;
    private readonly TextBox patient;
    private readonly TextBox staff;

    internal ProgramEditor(JsonObject? source, Dictionary<string, string> types)
    {
        original = source ?? new JsonObject();
        roomTypes = types;
        Title = "核对门诊空间清单";
        ClientSize = new Size(760, 650);
        Padding = new Padding(14);
        corridor = Field("corridor_width_m");
        door = Field("door_width_m");
        required = RelationField("required_connections");
        optional = RelationField("optional_connections");
        forbidden = RelationField("forbidden_connections");
        sight = Field("sight_target");
        patient = RouteField("patient_route");
        staff = RouteField("staff_route");
        if (original["rooms"] is JsonArray existing)
            foreach (var room in existing.OfType<JsonObject>())
                AddRoom(room);
        if (rooms.Count == 0)
        {
            AddRoom(null);
            AddRoom(null);
        }
        var add = new Button { Text = "添加房间" };
        add.Click += (_, _) => AddRoom(null);
        var accept = new Button { Text = "确认空间清单" };
        accept.Click += (_, _) => Confirm();
        var cancel = new Button { Text = "取消" };
        cancel.Click += (_, _) => Close(null);
        DefaultButton = accept;
        AbortButton = cancel;
        var notes = new List<string>();
        if (original["missing"] is JsonArray missing)
            notes.AddRange(missing.Select(item => item?.ToString() ?? ""));
        if (original["assumptions"] is JsonArray assumptions)
            notes.AddRange(assumptions.Select(item => item?.ToString() ?? ""));
        var description = notes.Count == 0 ? "所有长度与面积分别用米和平方米。可选连接不是必须开门。"
            : string.Join("；", notes);
        var body = ChatLayout.Column(6, 6);
        body.Items.Add(new Label { Text = description, Wrap = WrapMode.Word });
        body.Items.Add(new Label { Text = "房间 ID       房间名称                        功能类别                最小 / 最大面积（m²）" });
        body.Items.Add(table);
        body.Items.Add(ChatLayout.Row(add, new TableCell(null, true)));
        body.Items.Add(ChatLayout.Row(new Label { Text = "走廊净宽（m）" }, new TableCell(corridor, true),
            new Label { Text = "门洞宽度（m）" }, new TableCell(door, true)));
        body.Items.Add(new Label { Text = "直连关系用房间 ID 填写，例如 R1,R2；R2,R3。留空表示未指定。", Wrap = WrapMode.Word });
        foreach (var (caption, field) in new[] { ("必连", required), ("可选", optional), ("禁连", forbidden), ("视线目标 ID", sight),
                     ("患者路线（起点,终点）", patient), ("医护路线（起点,终点）", staff) })
            body.Items.Add(ChatLayout.Row(new Label { Text = caption, Width = 156 }, new TableCell(field, true)));
        body.Items.Add(new Label { Text = "入口用 @entry 表示；未填写的评估项标记为未评估。", Wrap = WrapMode.Word });
        var chrome = ChatLayout.Column(8);
        chrome.Items.Add(new StackLayoutItem(new Scrollable { Content = body, ExpandContentWidth = true },
            HorizontalAlignment.Stretch, expand: true));
        chrome.Items.Add(ChatLayout.Row(new TableCell(null, true), cancel, accept));
        Content = chrome;
    }

    private TextBox Field(string name) => new() { Text = original[name]?.ToString() ?? "" };

    private TextBox RelationField(string name) => new()
    {
        Text = original[name] is JsonArray relations
            ? string.Join("; ", relations.OfType<JsonArray>().Select(pair => string.Join(",", pair.Select(item => item?.ToString()))))
            : ""
    };

    private TextBox RouteField(string name) => new()
    {
        Text = original[name] is JsonArray route ? string.Join(",", route.Select(item => item?.ToString())) : ""
    };

    private void AddRoom(JsonObject? room)
    {
        if (rooms.Count >= 12)
        {
            MessageBox.Show(this, "首版支持最多 12 间房。");
            return;
        }
        var id = room?["id"]?.ToString() ?? Enumerable.Range(1, 24).Select(index => $"R{index}")
            .First(value => rooms.All(existing => existing.Id != value));
        var row = new RoomFields(id, room, roomTypes);
        var remove = new Button { Text = "移除" };
        var container = new DynamicLayout { Spacing = new Size(6, 0) };
        container.AddRow(new Label { Text = id, Width = 44 }, row.Name, row.Type, row.Low, row.High, remove);
        table.Items.Add(container);
        rooms.Add(row);
        remove.Click += (_, _) =>
        {
            if (rooms.Count <= 2)
                return;
            var item = table.Items.First(entry => entry.Control == container);
            table.Items.Remove(item);
            rooms.Remove(row);
        };
    }

    private void Confirm()
    {
        try
        {
            var ids = rooms.Select(row => row.Id).ToHashSet(StringComparer.Ordinal);
            var result = (JsonObject)original.DeepClone();
            result["rooms"] = new JsonArray(rooms.Select(row => (JsonNode)row.Build()).ToArray());
            result["corridor_width_m"] = Positive(corridor.Text, "走廊净宽", 0.5, 5);
            result["door_width_m"] = Positive(door.Text, "门洞宽度", 0.5, 5);
            result["required_connections"] = Relations(required.Text, ids);
            result["optional_connections"] = Relations(optional.Text, ids);
            result["forbidden_connections"] = Relations(forbidden.Text, ids);
            if (string.IsNullOrWhiteSpace(sight.Text))
                result["sight_target"] = null;
            else if (ids.Contains(sight.Text.Trim()))
                result["sight_target"] = sight.Text.Trim();
            else
                throw new InvalidOperationException("视线目标必须是当前清单里的房间 ID。");
            ids.Add("@entry");
            result["patient_route"] = string.IsNullOrWhiteSpace(patient.Text) ? null : Pair(patient.Text, ids);
            result["staff_route"] = string.IsNullOrWhiteSpace(staff.Text) ? null : Pair(staff.Text, ids);
            Close(result);
        }
        catch (InvalidOperationException exception)
        {
            MessageBox.Show(this, exception.Message, "请检查清单");
        }
    }

    private static JsonArray Relations(string text, HashSet<string> ids) => new(text
        .Split([';', '；', '\n'], StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
        .Select(value => (JsonNode)Pair(value, ids)).ToArray());

    private static JsonArray Pair(string text, HashSet<string> ids)
    {
        var parts = text.Split([',', '，'], StringSplitOptions.TrimEntries);
        if (parts.Length != 2 || parts[0] == parts[1] || parts.Any(part => !ids.Contains(part)))
            throw new InvalidOperationException($"关系或路线「{text}」需要两个不同且有效的端点 ID。");
        return new JsonArray(JsonValue.Create(parts[0]), JsonValue.Create(parts[1]));
    }

    private static double Positive(string text, string label, double min, double max)
    {
        if (!double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) ||
            !double.IsFinite(value) || value < min || value > max)
            throw new InvalidOperationException($"{label}需要填写 {min}–{max} 之间的数字，使用小数点。");
        return value;
    }

    private sealed class RoomFields
    {
        private readonly JsonObject? source;
        internal string Id { get; }
        internal TextBox Name { get; }
        internal DropDown Type { get; }
        internal TextBox Low { get; }
        internal TextBox High { get; }

        internal RoomFields(string id, JsonObject? room, Dictionary<string, string> types)
        {
            Id = id;
            source = room;
            Name = new TextBox { Text = room?["name"]?.ToString() ?? "", Width = 155 };
            Type = new DropDown { Width = 135 };
            foreach (var type in types)
                Type.Items.Add(new ListItem { Key = type.Key, Text = type.Value });
            Type.SelectedKey = room?["type"]?.ToString() ?? "consultation";
            Low = new TextBox { Text = room?["min_area_m2"]?.ToString() ?? "", Width = 62 };
            High = new TextBox { Text = room?["max_area_m2"]?.ToString() ?? "", Width = 62 };
            var provenance = room?["note"]?.ToString() ?? room?["source"]?.ToString();
            if (!string.IsNullOrWhiteSpace(provenance))
                Name.ToolTip = provenance;
        }

        internal JsonObject Build()
        {
            if (string.IsNullOrWhiteSpace(Name.Text) || string.IsNullOrEmpty(Type.SelectedKey))
                throw new InvalidOperationException($"{Id} 缺少房间名称或功能类型。");
            var low = Positive(Low.Text, $"{Id} 最小面积", 0.01, 100);
            var high = Positive(High.Text, $"{Id} 最大面积", low, 100);
            var room = source is null ? new JsonObject() : (JsonObject)source.DeepClone();
            room["id"] = Id;
            room["name"] = Name.Text.Trim();
            room["type"] = Type.SelectedKey;
            room["min_area_m2"] = low;
            room["max_area_m2"] = high;
            return room;
        }
    }
}
