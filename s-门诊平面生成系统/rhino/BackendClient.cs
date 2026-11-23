using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Eto.Forms;

namespace OutpatientRhino;

internal sealed class BackendClient
{
    private const string BackendRelative = "s-门诊平面生成系统/backend/run.py";
    private const string PythonRelative = ".venv/gcn-win/Scripts/python.exe";
    private const string SettingKey = "OutpatientRepositoryRoot";

    internal static string? FindRoot()
    {
        var candidates = new[] { Environment.GetEnvironmentVariable("OUTPATIENT_REPO_ROOT"),
            OutpatientPlugin.Instance?.Settings.GetString(SettingKey, ""), Path.GetDirectoryName(typeof(BackendClient).Assembly.Location) };
        foreach (var candidate in candidates)
        {
            if (string.IsNullOrWhiteSpace(candidate) || !Directory.Exists(candidate))
                continue;
            var path = new DirectoryInfo(candidate);
            for (var directory = path; directory is not null; directory = directory.Parent)
                if (IsRoot(directory.FullName))
                    return directory.FullName;
        }
        return null;
    }

    internal static bool IsRoot(string path) => File.Exists(Path.Combine(path, BackendRelative));

    internal static void SetRoot(string path) => OutpatientPlugin.Instance?.Settings.SetString(SettingKey, path);

    private static string RequireRoot() => FindRoot() ??
        throw new InvalidOperationException("未找到项目后端。请点击「设置项目目录」，选择 thesis-writing 仓库根目录。");

    internal static string ExampleText() => File.ReadAllText(Path.Combine(RequireRoot(),
        "s-门诊平面生成系统/backend/examples/l_shape.json"), Encoding.UTF8);

    internal static Dictionary<string, string> RoomTypes()
    {
        using var source = JsonDocument.Parse(File.ReadAllText(Path.Combine(RequireRoot(),
            "p-平面标注与数据处理/训练数据/单层医院_v1/vocabulary.json"), Encoding.UTF8));
        return source.RootElement.GetProperty("type_names").EnumerateObject().Where(item => item.Name != "corridor")
            .ToDictionary(item => item.Name, item => item.Value.GetString() ?? item.Name);
    }

    internal async Task<JsonElement> InvokeAsync(string operation, object request, bool allowApi,
        Action<JsonElement> progress, CancellationToken cancellation)
    {
        var root = RequireRoot();
        var python = Path.Combine(root, PythonRelative);
        if (!File.Exists(python))
            throw new InvalidOperationException("缺少后端 Python 环境。请先按 backend/README.md 配置。");
        var info = new ProcessStartInfo(python)
        {
            WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
            StandardInputEncoding = new UTF8Encoding(false), StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        foreach (var argument in new[] { "-B", "-X", "utf8", Path.Combine(root, BackendRelative), operation, "--pipe" })
            info.ArgumentList.Add(argument);
        if (allowApi)
            info.ArgumentList.Add("--allow-api");
        using var child = Process.Start(info) ?? throw new InvalidOperationException("无法启动后端进程。");
        using var registration = cancellation.Register(() =>
        {
            try
            {
                if (!child.HasExited)
                    child.Kill(entireProcessTree: true);
            }
            catch (InvalidOperationException) { }
            catch (System.ComponentModel.Win32Exception) { }
        });
        var stderr = child.StandardError.ReadToEndAsync();
        await child.StandardInput.WriteAsync(JsonSerializer.Serialize(request).AsMemory(), cancellation).ConfigureAwait(false);
        child.StandardInput.Close();
        JsonElement result = default;
        string? error = null;
        while (await child.StandardOutput.ReadLineAsync(cancellation).ConfigureAwait(false) is { } line)
        {
            using var document = JsonDocument.Parse(line);
            var message = document.RootElement;
            switch (message.String("kind"))
            {
                case "stage":
                case "text_delta":
                    var update = message.Clone();
                    Application.Instance.Invoke(() => progress(update));
                    break;
                case "result":
                    result = message.Clone();
                    break;
                case "error":
                    error = message.String("message");
                    break;
            }
        }
        await child.WaitForExitAsync(cancellation).ConfigureAwait(false);
        await stderr.ConfigureAwait(false);
        if (error is not null)
            throw new InvalidOperationException(error);
        if (result.ValueKind == JsonValueKind.Object && (child.ExitCode == 0 || child.ExitCode == 2))
            return result;
        throw new InvalidOperationException($"后端退出（代码 {child.ExitCode}）。请检查 Python 依赖、模型权重和 API 配置。");
    }
}

internal static class JsonValues
{
    internal static JsonElement Value(this JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var property) ? property : default;

    internal static string? String(this JsonElement element, string name) =>
        element.Value(name) is { ValueKind: JsonValueKind.String } value ? value.GetString() : null;

    internal static IEnumerable<JsonElement> Items(this JsonElement element, string name) =>
        element.Value(name) is { ValueKind: JsonValueKind.Array } values ? values.EnumerateArray() : [];

    internal static double? Number(this JsonElement element, string name) =>
        element.Value(name) is { ValueKind: JsonValueKind.Number } value && value.TryGetDouble(out var number) ? number : null;
}
