"""Exercise the local Rhino host in a new empty document without dependency on screen focus."""

from System import Activator, Array, DateTime, Environment, Guid, Object
from System.IO import File
from System.Reflection import BindingFlags
import Rhino


def trace(message):
    File.AppendAllText(Environment.GetEnvironmentVariable("OUTPATIENT_SMOKE_TRACE"), message + Environment.NewLine)


def member(panel, kind, name):
    flags = BindingFlags.Instance | BindingFlags.NonPublic
    found = getattr(panel.GetType(), kind)(name, flags)
    if found is None:
        raise Exception("Missing smoke target " + name)
    return found


def object_count(doc):
    return len(list(doc.Objects.GetObjectList(Rhino.DocObjects.ObjectType.AnyObject)))


def verify_chat_reply(panel, expected_plan):
    history = member(panel, "GetField", "conversationHistory").GetValue(panel)
    if history.Count == 0 or not list(history)[-1]["assistant"].strip():
        raise Exception("Expected a completed conversational reply")
    if member(panel, "GetField", "plan").GetValue(panel) != expected_plan:
        raise Exception("Chat changed the preview")
    chat = member(panel, "GetField", "chat").GetValue(panel)
    rows = member(chat, "GetField", "messages").GetValue(chat).Items
    replies = [row for row in rows if row.Control.GetType().Name == "MarkdownReply"]
    if len(replies) != history.Count:
        raise Exception("Expected one rendered answer per completed question")
    color = rows[1].Control.Items[0].Control.ControlObject.Background.Color
    if (color.R, color.G, color.B) != (231, 245, 235):
        raise Exception("Expected a pale green user bubble")
    if any(row.Control.GetType().Name == "ThinkingIndicator" for row in rows):
        raise Exception("A completed answer retained its thinking indicator")
    records = [row for row in rows if row.Control.GetType().Name == "AgentProgressCard"]
    if len(records) != (0 if expected_plan is None else 1):
        raise Exception("An ordinary question changed the number of retained tool records")
    trace("DeepSeek replied through the composer")


def verify_agent_progress(panel, state):
    card = member(panel, "GetField", "latestProgress").GetValue(panel)
    if card is None:
        raise Exception("Missing agent progress card")
    if (DateTime.UtcNow - state["started"]).TotalSeconds > 90:
        raise Exception("Timed out rendering the agent timeline in Rhino")
    if "opened_progress" not in state:
        if member(card, "GetField", "details").GetValue(card).Visible:
            raise Exception("The elapsed-time row should start collapsed")
        toggle = member(card, "GetField", "toggle").GetValue(card)
        if not toggle.Text.startswith(u"\u7528\u65f6 ") or not toggle.Text.endswith(u"\u203a"):
            raise Exception("Missing compact elapsed-time label")
        if member(card, "GetField", "elapsed").GetValue(card).IsRunning:
            raise Exception("The completed run timer is still ticking")
        member(card, "GetMethod", "SetExpanded").Invoke(card, Array[Object]([True]))
        state["opened_progress"] = True
    if not member(card, "GetField", "ready").GetValue(card):
        return False
    browser = member(card, "GetField", "browser").GetValue(card)
    if "probe" not in state:
        # Exercise the same expand controls the designer uses in the transcript.
        state["probe"] = browser.ExecuteScriptAsync("""
            (() => {
                const titles = [...document.querySelectorAll('[class*="node-title"]')];
                if (titles.length !== 4) return false;
                if (!document.querySelector('[class*="think-status-wrapper"]')) return false;
                if (!document.querySelector('.events')) { titles[1].click(); return false; }
                const text = document.querySelector('.events').innerText;
                return text.includes('\u8fde\u901a\u5173\u7cfb\u9884\u6d4b') && text.includes('C01') && text.includes('T01')
                    && !!document.querySelector('.ant-descriptions');
            })()
        """)
        return False
    if not state["probe"].IsCompleted:
        return False
    value = state.pop("probe").GetAwaiter().GetResult()
    if value == "true":
        trace("PASS: collapsed duration expands to Think, four stages and GCN tools")
        return True
    return False


def verify_columns(panel):
    composer = member(panel, "GetField", "composer").GetValue(panel)
    chat = member(panel, "GetField", "chat").GetValue(panel)
    messages = member(chat, "GetField", "messages").GetValue(chat)
    greeting = messages.Items[0].Control
    trace("layout widths: host={0}, chat={1}, composer={2}, greeting={3}".format(
        panel.Width, chat.Width, composer.Width, greeting.Width))
    if (min(composer.Width, chat.Width) < panel.Width * 0.85 or
            not panel.Width * 0.75 <= greeting.Width <= chat.Width + 1):
        raise Exception("Narrow-panel regression: the transcript, greeting or composer does not fill the panel")


def verify_composer(panel):
    import clr
    clr.AddReference("WindowsBase")
    clr.AddReference("PresentationFramework")
    clr.AddReference("PresentationCore")
    from System.Windows import Point
    editor = member(panel, "GetField", "composer").GetValue(panel)
    action = member(panel, "GetField", "composerAction").GetValue(panel)
    box, button = editor.ControlObject, action.ControlObject
    box.ApplyTemplate()
    button.ApplyTemplate()
    hint = box.Template.FindName("Hint", box)
    disc = button.Template.FindName("Disc", button)
    arrow = button.Template.FindName("SendIcon", button)
    if not hint.IsVisible or hint.Text != u"\u53d1\u6d88\u606f..." or not arrow.IsVisible or action.Enabled:
        raise Exception("Expected the lowered placeholder and disabled send arrow")
    hint_origin = hint.TranslatePoint(Point(0, 0), box)
    if hint_origin.Y < 10 or hint.Foreground.Color.R < 145:
        raise Exception("Placeholder inset or gray color was lost")
    from System.Windows.Media import SolidColorBrush
    if str(disc.Fill.Color) != "#FFEDF0EE":
        raise Exception("Expected a pale gray empty button")
    editor.Text = "   "
    if action.Enabled:
        raise Exception("Whitespace enabled sending")
    editor.Text = u"\u9996\u5c42\n\u5165\u53e3"
    box.UpdateLayout()
    caret = box.GetRectFromCharacterIndex(0)
    target = disc.Fill.GetAnimationBaseValue(SolidColorBrush.ColorProperty)
    if not action.Enabled or hint.IsVisible or not arrow.IsVisible or str(target) != "#FFB8EACD":
        raise Exception("Typing should enable a mint send button")
    if str(box.Foreground.Color) != "#FF000000" or str(box.CaretBrush.Color) != "#FF000000":
        raise Exception("Expected black input text and caret")
    if abs(caret.Y - hint_origin.Y) > 2 or abs(caret.X - hint_origin.X) > 3:
        raise Exception("Text starts at {0} while the placeholder starts at {1}".format(caret, hint_origin))
    editor.Text = ""
    trace("PASS: inset placeholder, aligned first line, disabled and enabled send arrow")


def verify_pick_glow_and_drop(panel):
    from System import Action, String, Uri
    from System.IO import Path
    from Eto.Forms import DataObject, DragEventArgs, DragEffects, Keys, MouseButtons
    from Eto.Drawing import PointF
    flags = BindingFlags.NonPublic | BindingFlags.Instance
    assembly = panel.GetType().Assembly
    def component(name, arg):
        constructor = assembly.GetType("OutpatientRhino." + name).GetConstructors(flags)[0]
        return constructor.Invoke(Array[Object]([arg]))

    glow = member(panel, "GetMethod", "BeginBoundaryPick").Invoke(panel, None)
    layer = member(glow, "GetField", "layer").GetValue(glow)
    target = glow.AdornedElement
    try:
        target.UpdateLayout()
        if glow not in layer.GetAdorners(target) or glow.IsHitTestVisible or glow.Effect is None:
            raise Exception("Expected a non-interactive glow on the plug-in panel")
        if not 0.25 <= glow.Opacity <= 0.56 or glow.Effect.Opacity > 0.3:
            raise Exception("The pick indicator is too bright or too faint")
        if abs(target.ActualWidth - panel.Width) > 20:
            raise Exception("Glow does not match the plug-in width")
    finally:
        glow.Dispose()
    if glow in (layer.GetAdorners(target) or []):
        raise Exception("Panel glow remained after disposal")
    trace("PASS: glow matches plugin width, ignores input and is removed")
    accepted = []
    upload = component("BriefUpload", Action[String](accepted.append))
    button = member(upload, "GetField", "choose").GetValue(upload)
    path = Path.Combine(Path.GetTempPath(), str(Guid.NewGuid()) + ".txt")
    File.WriteAllText(path, "test")
    try:
        for candidate, valid in [(path + ".png", False), (path, True)]:
            data = DataObject()
            data.Uris = Array[Uri]([Uri(candidate)])
            args = DragEventArgs(button, data, DragEffects.Copy, PointF(2, 2), getattr(Keys, "None"), getattr(MouseButtons, "None"))
            member(button, "GetMethod", "OnDragOver").Invoke(button, Array[Object]([args]))
            if (args.Effects == DragEffects.Copy) != valid:
                raise Exception("Wrong drop effect")
            member(button, "GetMethod", "OnDragDrop").Invoke(button, Array[Object]([args]))
        if accepted != [path]:
            raise Exception("Upload did not accept exactly the supported local file")
        trace("PASS: dropping TXT selects its path; unsupported drop is rejected")
    finally:
        File.Delete(path)
        upload.Dispose()


def capture_panel(panel, target):
    import clr
    clr.AddReference("PresentationCore")
    from System.Windows.Media import PixelFormats
    from System.Windows.Media.Imaging import BitmapFrame, PngBitmapEncoder, RenderTargetBitmap
    visual = panel.ControlObject
    visual.UpdateLayout()
    image = RenderTargetBitmap(panel.Width, panel.Height, 96.0, 96.0, PixelFormats.Pbgra32)
    image.Render(visual)
    encoder = PngBitmapEncoder()
    encoder.Frames.Add(BitmapFrame.Create(image))
    with File.OpenWrite(target) as output:
        encoder.Save(output)


def main():
    path = Environment.GetEnvironmentVariable("OUTPATIENT_RHP_TO_LOAD")
    result, plugin_id = Rhino.PlugIns.PlugIn.LoadPlugIn(path)
    if result != Rhino.PlugIns.LoadPlugInResult.Success:
        raise Exception("Plugin load failed: " + str(result))
    Rhino.UI.Panels.OpenPanel(Guid("1d710de3-fcb6-478b-9b95-69231350ee79"))
    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None or object_count(doc):
        raise Exception("Smoke test requires a new empty Rhino document")
    panel = Rhino.UI.Panels.GetPanel(Guid("1d710de3-fcb6-478b-9b95-69231350ee79"), doc)
    if panel is None:
        raise Exception("Docked panel was not created")
    member(panel, "GetField", "composer")
    trace("loaded chat panel in Rhino " + str(Rhino.RhinoApp.Version))
    trace("plug-in: " + panel.GetType().Assembly.Location)
    if panel.GetType().Assembly.Location.lower() != path.lower():
        raise Exception("Rhino loaded a different plug-in build")
    live_chat = Environment.GetEnvironmentVariable("OUTPATIENT_SMOKE_LIVE_CHAT") == "1"
    width = Environment.GetEnvironmentVariable("OUTPATIENT_SMOKE_WIDTH")
    form = None
    if width:
        from Eto.Drawing import Size
        from Eto.Forms import Form
        panel = Activator.CreateInstance(panel.GetType())
        form = Form()
        form.Title = "Outpatient - narrow layout test"
        form.ClientSize = Size(int(width), 710)
        form.Content = panel
        form.Show()
    state = {"task": None, "preview_idle": False, "started": DateTime.UtcNow}

    def on_idle(sender, args):
        try:
            if state["task"] is None:
                if width and panel.Width < 200:
                    if (DateTime.UtcNow - state["started"]).TotalSeconds > 15:
                        raise Exception("Rhino did not lay out the narrow test panel")
                    return
                if width:
                    if abs(panel.Width - int(width)) > 10:
                        raise Exception("The requested narrow test width was not applied")
                    verify_columns(panel)
                    verify_composer(panel)
                    verify_pick_glow_and_drop(panel)
                for name in ("status", "options", "settings", "editProgram"):
                    if member(panel, "GetField", name).GetValue(panel).Visible:
                        raise Exception("Unexpected startup control: " + name)
                if not member(panel, "GetField", "add").GetValue(panel).Enabled:
                    raise Exception("Missing startup actions")
                for name in ("attachBrief", "selectBoundary", "simpleDesign"):
                    button = member(panel, "GetField", name).GetValue(panel)
                    if not button.Enabled or not button.Visible or not button.Text:
                        raise Exception("Missing welcome button: " + name)
                landing = Environment.GetEnvironmentVariable("OUTPATIENT_SMOKE_LANDING")
                if landing:
                    capture_panel(panel, landing)
                if live_chat:
                    composer = member(panel, "GetField", "composer").GetValue(panel)
                    composer.Text = u"\u4f60\u597d"
                    state["phase"] = "greeting"
                    state["task"] = member(panel, "GetMethod", "SendFromComposerAsync").Invoke(panel, None)
                    return
                state["task"] = member(panel, "GetMethod", "StartSimpleDesignAsync").Invoke(panel, None)
                return
            if not state["task"].IsCompleted:
                if state.get("phase") == "greeting":
                    chat = member(panel, "GetField", "chat").GetValue(panel)
                    rows = member(chat, "GetField", "messages").GetValue(chat).Items
                    last = rows[rows.Count - 1].Control
                    if last.GetType().Name == "MarkdownReply":
                        native = member(last, "GetField", "fallback").GetValue(last)
                        view = member(last, "GetField", "view").GetValue(last)
                        if native.IsVisible and native.Text and str(view.Visibility) != "Collapsed":
                            raise Exception("Native reply appeared before the Markdown handoff")
                return
            if state.get("phase") == "greeting":
                state["task"].GetAwaiter().GetResult()
                verify_chat_reply(panel, None)
                state["phase"] = "example"
                request = u"\u751f\u6210\u793a\u4f8b"
                state["task"] = member(panel, "GetMethod", "SubmitAsync").Invoke(panel, Array[Object]([request]))
                return
            if state.get("phase") == "example":
                state["task"].GetAwaiter().GetResult()
                state["plan"] = member(panel, "GetField", "plan").GetValue(panel)
                if state["plan"] is None:
                    raise Exception("Expected a preview before chat")
                composer = member(panel, "GetField", "composer").GetValue(panel)
                composer.Text = u"\u963f\u8428"
                state["phase"] = "after_preview"
                state["task"] = member(panel, "GetMethod", "SendFromComposerAsync").Invoke(panel, None)
                return
            if state.get("phase") == "after_preview":
                state["task"].GetAwaiter().GetResult()
                verify_chat_reply(panel, state["plan"])
                if member(panel, "GetField", "conversationHistory").GetValue(panel).Count != 2:
                    raise Exception("Chat after generating did not complete: " + member(panel, "GetField", "status").GetValue(panel).Text)
                state["phase"] = "done"
            if not state["preview_idle"]:
                state["preview_idle"] = True
                return
            if not live_chat and not verify_agent_progress(panel, state):
                return
            Rhino.RhinoApp.Idle -= on_idle
            state["task"].GetAwaiter().GetResult()
            plan = member(panel, "GetField", "plan").GetValue(panel)
            if plan is None:
                label = member(panel, "GetField", "status").GetValue(panel)
                raise Exception("No Rhino preview: " + label.Text)
            for name in ("settings", "editProgram"):
                if not member(panel, "GetField", name).GetValue(panel).Visible:
                    raise Exception("Missing action after boundary selection: " + name)
            if object_count(doc):
                raise Exception("Preview unexpectedly added Rhino document objects")
            if member(panel, "GetField", "resultWrite").GetValue(panel) is None:
                raise Exception("Chat result card did not expose a write action")
            if width:
                form.ControlObject.UpdateLayout()
                result_state = member(panel, "GetField", "resultState").GetValue(panel)
                trace("result content width: {0}".format(result_state.Width))
                if result_state.Width < panel.Width * 0.65:
                    raise Exception("The narrow layout clipped the result card")
                chat = member(panel, "GetField", "chat").GetValue(panel)
                viewer = member(chat, "GetProperty", "NativeViewer").GetValue(chat)
                if viewer is None:
                    raise Exception("The Rhino transcript did not expose a native scroll viewer")
                trace("chat scroll: {0}/{1}".format(viewer.VerticalOffset, viewer.ScrollableHeight))
                if viewer.ScrollableHeight - viewer.VerticalOffset > 3:
                    raise Exception("The transcript did not scroll to the latest result")
            screenshot = Environment.GetEnvironmentVariable("OUTPATIENT_SMOKE_PREVIEW")
            if screenshot:
                capture_panel(panel, screenshot)
                trace("captured rendered chat panel")
            if width:
                viewport = viewer.Template.FindName("PART_ScrollContentPresenter", viewer)
                if str(chat.Border) != "None" or viewer.VerticalOffset <= 0 or viewport.OpacityMask is None:
                    raise Exception("Expected a borderless transcript with a top fade after scrolling")
                viewer.ScrollToTop()
                viewer.UpdateLayout()
                if viewer.VerticalOffset != 0 or viewport.OpacityMask is not None:
                    raise Exception("The first message must be fully visible at the top")
                trace("PASS: borderless transcript fades on scroll and clears at the top")
                long_text = (u"\u95e8\u8bca\u7a7a\u95f4" + "VeryLongRoomIdentifier" * 5) * 4
                member(chat, "GetMethod", "Say").Invoke(chat, Array[Object]([long_text, True]))
                for test_width in (560, 320):
                    form.ClientSize = Size(test_width, 710)
                    form.ControlObject.UpdateLayout()
                    viewer.UpdateLayout()
                    if (str(viewer.ComputedHorizontalScrollBarVisibility) == "Visible" or
                            viewer.ScrollableWidth > 1 or result_state.Width > viewer.ViewportWidth):
                        raise Exception("Transcript overflows at {0}: viewport={1}, extent={2}, card={3}".format(
                            test_width, viewer.ViewportWidth, viewer.ExtentWidth, result_state.Width))
                bar = viewer.Template.FindName("PART_VerticalScrollBar", viewer)
                track = bar.Template.FindName("PART_Track", bar)
                thumb_surface = track.Thumb.Template.FindName("Handle", track.Thumb)
                if not bar.IsVisible or thumb_surface.ActualWidth != 4:
                    raise Exception("Expected a four-unit scroll thumb")
                trace("PASS: long messages and result card fit after widening and narrowing")
            if live_chat:
                trace("PASS: live chat before boundary selection and after preview")
            trace("generated preview, with no document side effects")
            member(panel, "GetMethod", "WritePlan").Invoke(panel, None)
            count = object_count(doc)
            if count < 10:
                raise Exception("Expected room outlines, corridor, doors and labels")
            trace("committed {0} editable Rhino objects".format(count))
            target = Environment.GetEnvironmentVariable("OUTPATIENT_SMOKE_3DM")
            if target:
                options = Rhino.FileIO.FileWriteOptions()
                options.SuppressDialogBoxes = True
                if not doc.Write3dmFile(target, options):
                    raise Exception("Example 3dm export failed")
                trace("saved example .3dm")
            if not Rhino.RhinoApp.RunScript("_Undo", False) or object_count(doc):
                raise Exception("One Undo did not restore the empty document")
            trace("PASS: one Undo restored the empty document")
            if form:
                form.Close()
        except Exception as error:
            Rhino.RhinoApp.Idle -= on_idle
            trace("FAIL: " + str(error))
            if form:
                form.Close()

    Rhino.RhinoApp.Idle += on_idle


try:
    main()
except Exception as error:
    trace("FAIL: " + str(error))
