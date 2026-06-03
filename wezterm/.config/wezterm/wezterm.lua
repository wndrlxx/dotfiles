local wezterm = require("wezterm")
local config = wezterm.config_builder()

config.font = wezterm.font("JetBrainsMono Nerd Font")
config.font_size = 16.0

config.window_background_opacity = 0.99
config.macos_window_background_blur = 20

config.window_decorations = "RESIZE"
config.window_padding = {
	left = 2,
	right = 2,
	top = 0,
	bottom = 0,
}

config.hide_tab_bar_if_only_one_tab = true
config.use_fancy_tab_bar = false
config.show_new_tab_button_in_tab_bar = false
config.show_tab_index_in_tab_bar = true

wezterm.on("window-config-reloaded", function(window, pane)
	local overrides = window:get_config_overrides() or {}
	local appearance = window:get_appearance()
	if appearance:find("Dark") then
		overrides.color_scheme = "tokyonight"
	else
		overrides.color_scheme = "rose-pine-dawn"
	end
	window:set_config_overrides(overrides)
end)

config.keys = {
	{
		key = "Space",
		mods = "SUPER|SHIFT",
		action = wezterm.action.QuickSelect,
	},
	{
		key = "X",
		mods = "SUPER|SHIFT",
		action = wezterm.action.ActivateCopyMode,
	},
	{
		key = "|",
		mods = "SUPER|SHIFT",
		action = wezterm.action.SplitPane({
			direction = "Right",
		}),
	},
	{
		key = "-",
		mods = "SUPER",
		action = wezterm.action.DisableDefaultAssignment,
	},
	{
		key = "_",
		mods = "SUPER|SHIFT",
		action = wezterm.action.SplitPane({
			direction = "Down",
		}),
	},
	{
		key = "h",
		mods = "SUPER|ALT",
		action = wezterm.action.ActivatePaneDirection("Left"),
	},
	{
		key = "j",
		mods = "SUPER|ALT",
		action = wezterm.action.ActivatePaneDirection("Down"),
	},
	{
		key = "k",
		mods = "SUPER|ALT",
		action = wezterm.action.ActivatePaneDirection("Up"),
	},
	{
		key = "l",
		mods = "SUPER|ALT",
		action = wezterm.action.ActivatePaneDirection("Right"),
	},
	{
		key = "z",
		mods = "SUPER|ALT",
		action = wezterm.action.TogglePaneZoomState,
	},
	{
		key = "w",
		mods = "SUPER",
		action = wezterm.action.CloseCurrentPane({ confirm = false }),
	},
	{
		key = "h",
		mods = "SUPER|SHIFT",
		action = wezterm.action.AdjustPaneSize({ "Left", 4 }),
	},
	{
		key = "j",
		mods = "SUPER|SHIFT",
		action = wezterm.action.AdjustPaneSize({ "Down", 4 }),
	},
	{
		key = "k",
		mods = "SUPER|SHIFT",
		action = wezterm.action.AdjustPaneSize({ "Up", 4 }),
	},
	{
		key = "l",
		mods = "SUPER|SHIFT",
		action = wezterm.action.AdjustPaneSize({ "Right", 4 }),
	},
}

return config
