"""Load the locally built plug-in when invoked from Rhino's scripting host."""

from System import Environment, Guid, String, StringComparison
import Rhino


def main():
    path = Environment.GetEnvironmentVariable("OUTPATIENT_RHP_TO_LOAD")
    if not path:
        Rhino.RhinoApp.WriteLine("No OutpatientRhino path was supplied; use PlugInManager instead.")
        return
    try:
        loaded = Rhino.PlugIns.PlugIn.Find(Guid("0156ac98-6880-4a24-8584-d461fa55fb78"))
        if loaded is not None and String.Equals(loaded.GetType().Assembly.Location, path, StringComparison.OrdinalIgnoreCase):
            Rhino.RhinoApp.RunScript("_OutpatientPlanner", False)
            return
        result, plugin_id = Rhino.PlugIns.PlugIn.LoadPlugIn(path)
        if result == Rhino.PlugIns.LoadPlugInResult.Success:
            Rhino.RhinoApp.WriteLine("OutpatientRhino loaded: {0}".format(plugin_id))
            Rhino.RhinoApp.RunScript("_OutpatientPlanner", False)
        else:
            Rhino.RhinoApp.WriteLine("OutpatientRhino load failed: {0}. Check PlugInManager.".format(result))
    except Exception as error:
        Rhino.RhinoApp.WriteLine("OutpatientRhino: {0}".format(error))


main()
