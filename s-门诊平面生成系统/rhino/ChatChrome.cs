using Eto.Drawing;
using Eto.Forms;
using AutomationProperties = System.Windows.Automation.AutomationProperties;
using Border = System.Windows.Controls.Border;
using CornerRadius = System.Windows.CornerRadius;
using Thickness = System.Windows.Thickness;
using Media = System.Windows.Media;

namespace OutpatientRhino;

internal static class ChatChrome
{
    private static readonly Media.Brush Frame = Brush(161, 161, 161);
    private static readonly Media.Brush Accent = Brush(40, 40, 40);
    private static readonly Media.Brush Disabled = Brush(231, 231, 231);
    private static readonly Media.Brush Ink = Brush(30, 30, 30);
    private static readonly Media.Brush Muted = Brush(76, 76, 76);

    internal static readonly System.Windows.Controls.ControlTemplate ScrollBarTemplate =
        (System.Windows.Controls.ControlTemplate)System.Windows.Markup.XamlReader.Parse("""
            <ControlTemplate xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" TargetType="ScrollBar">
              <ControlTemplate.Resources>
                <ControlTemplate x:Key="TrackArea" TargetType="RepeatButton">
                  <Border Background="Transparent"/>
                </ControlTemplate>
              </ControlTemplate.Resources>
              <Track x:Name="PART_Track" IsDirectionReversed="True" Orientation="Vertical">
                <Track.DecreaseRepeatButton>
                  <RepeatButton Template="{StaticResource TrackArea}" Command="ScrollBar.PageUpCommand" Focusable="False"/>
                </Track.DecreaseRepeatButton>
                <Track.Thumb>
                  <Thumb MinHeight="20">
                    <Thumb.Template>
                      <ControlTemplate TargetType="Thumb">
                        <Grid Background="Transparent">
                          <Border x:Name="Handle" Width="4" CornerRadius="2" Background="#A0A0A0"/>
                        </Grid>
                        <ControlTemplate.Triggers>
                          <Trigger Property="IsMouseOver" Value="True">
                            <Setter TargetName="Handle" Property="Background" Value="#727272"/>
                          </Trigger>
                          <Trigger Property="IsDragging" Value="True">
                            <Setter TargetName="Handle" Property="Background" Value="#555555"/>
                          </Trigger>
                        </ControlTemplate.Triggers>
                      </ControlTemplate>
                    </Thumb.Template>
                  </Thumb>
                </Track.Thumb>
                <Track.IncreaseRepeatButton>
                  <RepeatButton Template="{StaticResource TrackArea}" Command="ScrollBar.PageDownCommand" Focusable="False"/>
                </Track.IncreaseRepeatButton>
              </Track>
            </ControlTemplate>
            """);

    internal static Panel Rounded(Control content, Color fill, Padding padding, double radius, bool outlined = false)
    {
        var surface = new Panel { Content = content, BackgroundColor = fill, Padding = padding };
        if (surface.ControlObject is Border border)
        {
            border.CornerRadius = new CornerRadius(radius);
            if (outlined)
            {
                border.BorderThickness = new Thickness(1);
                border.BorderBrush = Frame;
            }
        }
        return surface;
    }

    internal static Panel Composer(TextArea editor, Button add, Button action)
    {
        var content = ChatLayout.Column(4);
        content.Items.Add(editor);
        content.Items.Add(ChatLayout.Row(add, new TableCell(null, true), action));
        var surface = Rounded(content, Colors.White, new Padding(9, 6), 16, outlined: true);
        if (editor.ControlObject is System.Windows.Controls.TextBox textbox)
        {
            textbox.BorderThickness = new Thickness(0);
            textbox.Padding = new Thickness(0);
            textbox.Foreground = Media.Brushes.Black;
            textbox.CaretBrush = textbox.Foreground;
            AutomationProperties.SetName(textbox, "发消息");
            textbox.Template = (System.Windows.Controls.ControlTemplate)System.Windows.Markup.XamlReader.Parse("""
                <ControlTemplate xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                                 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" TargetType="TextBox">
                  <Border Background="Transparent" Padding="7,11,4,0">
                    <Grid>
                      <ScrollViewer x:Name="PART_ContentHost" Focusable="False"
                                    HorizontalScrollBarVisibility="Disabled" VerticalScrollBarVisibility="Auto"/>
                      <TextBlock x:Name="Hint" Text="发消息..." Foreground="#979C99" Margin="2,0,0,0"
                                 VerticalAlignment="Top" Visibility="Collapsed" IsHitTestVisible="False"/>
                    </Grid>
                  </Border>
                  <ControlTemplate.Triggers>
                    <Trigger Property="Text" Value="">
                      <Setter TargetName="Hint" Property="Visibility" Value="Visible"/>
                    </Trigger>
                  </ControlTemplate.Triggers>
                </ControlTemplate>
                """);
        }
        if (surface.ControlObject is Border frame)
        {
            var idleEdge = Brush(200, 205, 202);
            var greenEdge = Brush(78, 182, 139);
            var shadow = new Media.Effects.DropShadowEffect();
            frame.Effect = shadow;
            void RefreshGlow()
            {
                var focused = editor.HasFocus || action.Enabled;
                frame.BorderBrush = focused ? greenEdge : idleEdge;
                shadow.Color = focused ? Media.Color.FromRgb(52, 205, 142) : Media.Colors.Black;
                shadow.BlurRadius = focused ? 15 : 9;
                shadow.ShadowDepth = focused ? 0 : 2;
                shadow.Direction = 270;
                shadow.Opacity = focused ? 0.34 : 0.13;
            }
            editor.GotFocus += (_, _) => RefreshGlow();
            editor.LostFocus += (_, _) => RefreshGlow();
            if (action.ControlObject is System.Windows.Controls.Button nativeAction)
                nativeAction.IsEnabledChanged += (_, _) => RefreshGlow();
            RefreshGlow();
        }
        return surface;
    }

    internal static Button AddButton()
    {
        var button = new Button { Text = "＋", Width = 30, Height = 30 };
        if (button.ControlObject is not System.Windows.Controls.Button native)
            return button;
        native.MinWidth = 0;
        AutomationProperties.SetName(native, "添加");
        native.Template = (System.Windows.Controls.ControlTemplate)System.Windows.Markup.XamlReader.Parse("""
            <ControlTemplate xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" TargetType="Button">
              <Border x:Name="HitArea" Background="Transparent" CornerRadius="15">
                <Path Data="M 0,7 L 14,7 M 7,0 L 7,14" Stroke="#404040" StrokeThickness="1.5"
                      HorizontalAlignment="Center" VerticalAlignment="Center"/>
              </Border>
              <ControlTemplate.Triggers>
                <Trigger Property="IsMouseOver" Value="True">
                  <Setter TargetName="HitArea" Property="Background" Value="#EFEFEF"/>
                </Trigger>
                <Trigger Property="IsKeyboardFocused" Value="True">
                  <Setter TargetName="HitArea" Property="Background" Value="#E6E6E6"/>
                </Trigger>
                <Trigger Property="IsEnabled" Value="False">
                  <Setter TargetName="HitArea" Property="Opacity" Value="0.45"/>
                </Trigger>
              </ControlTemplate.Triggers>
            </ControlTemplate>
            """);
        return button;
    }

    internal static Button ComposerActionButton()
    {
        var button = new Button { Text = "发送消息", Width = 30, Height = 30, Enabled = false };
        if (button.ControlObject is System.Windows.Controls.Button native)
        {
            native.MinWidth = 0;
            var empty = Media.Color.FromRgb(237, 240, 238);
            var mint = Media.Color.FromRgb(184, 234, 205);
            var fill = new Media.SolidColorBrush(empty);
            native.Background = fill;
            native.IsEnabledChanged += (_, _) =>
            {
                var start = fill.Color;
                var target = native.IsEnabled ? mint : empty;
                fill.Color = target;
                var fade = System.Windows.SystemParameters.ClientAreaAnimation
                    ? new Media.Animation.ColorAnimation(start, target, TimeSpan.FromMilliseconds(160))
                        { FillBehavior = Media.Animation.FillBehavior.Stop }
                    : null;
                fill.BeginAnimation(Media.SolidColorBrush.ColorProperty, fade);
            };
            using var source = typeof(ChatChrome).Assembly.GetManifestResourceStream("OutpatientRhino.ComposerAction.xaml")!;
            native.Template = (System.Windows.Controls.ControlTemplate)System.Windows.Markup.XamlReader.Load(source);
        }
        return button;
    }

    internal static void SetComposerAction(Button button, bool busy, bool enabled)
    {
        var caption = busy ? "停止当前任务" : "发送消息";
        if (button.ControlObject is System.Windows.Controls.Button native)
        {
            native.Tag = busy ? "Stop" : "Send";
            AutomationProperties.SetName(native, caption);
        }
        button.ToolTip = caption;
        button.Enabled = enabled;
    }

    // Rhino themes the Eto button's inner label independently of its WPF foreground.
    // Draw the caption and surface together so both use the same interaction state.
    private static readonly System.Windows.Controls.ControlTemplate ChatButtonTemplate =
        (System.Windows.Controls.ControlTemplate)System.Windows.Markup.XamlReader.Parse("""
            <ControlTemplate xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" TargetType="Button">
              <Border x:Name="Surface" Background="{TemplateBinding Background}"
                      BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="1"
                      CornerRadius="5" Padding="7,3">
                <TextBlock Text="{Binding Path=(AutomationProperties.Name), RelativeSource={RelativeSource TemplatedParent}}"
                           Foreground="{TemplateBinding Foreground}"
                           HorizontalAlignment="Center" VerticalAlignment="Center"/>
              </Border>
              <ControlTemplate.Triggers>
                <Trigger Property="IsMouseOver" Value="True">
                  <Setter TargetName="Surface" Property="BorderBrush" Value="#707070"/>
                </Trigger>
                <Trigger Property="IsKeyboardFocused" Value="True">
                  <Setter TargetName="Surface" Property="BorderBrush" Value="#737373"/>
                </Trigger>
                <Trigger Property="IsPressed" Value="True">
                  <Setter TargetName="Surface" Property="Opacity" Value="0.78"/>
                </Trigger>
              </ControlTemplate.Triggers>
            </ControlTemplate>
            """);

    internal static Button Button(string text, bool primary)
    {
        var button = new Button { Text = text };
        if (button.ControlObject is not System.Windows.Controls.Button native)
            return button;
        native.Template = ChatButtonTemplate;
        AutomationProperties.SetName(native, text);
        void Refresh()
        {
            native.Background = !native.IsEnabled ? Disabled : primary ? Accent : Media.Brushes.White;
            native.Foreground = !native.IsEnabled ? Muted : primary ? Media.Brushes.White : Ink;
            native.BorderBrush = native.IsEnabled && primary ? Accent : Frame;
        }
        native.IsEnabledChanged += (_, _) => Refresh();
        Refresh();
        return button;
    }

    private static Media.Brush Brush(byte red, byte green, byte blue)
    {
        var brush = new Media.SolidColorBrush(Media.Color.FromRgb(red, green, blue));
        brush.Freeze();
        return brush;
    }
}
