rex.bind("ctrl+alt+x", "pane.close")
rex.bind("ctrl+alt+\\", "pane.split.right")
rex.bind("ctrl+alt+-", "pane.split.down")

rex.unbind("alt+cmd+left", "pane.focus.left")
rex.unbind("alt+cmd+down", "pane.focus.down")
rex.unbind("alt+cmd+up", "pane.focus.up")
rex.unbind("alt+cmd+right", "pane.focus.right")
rex.bind("ctrl+alt+h", "pane.focus.left")
rex.bind("ctrl+alt+j", "pane.focus.down")
rex.bind("ctrl+alt+k", "pane.focus.up")
rex.bind("ctrl+alt+l", "pane.focus.right")

local resize_step = 5
rex.bind("ctrl+alt+shift+h", "pane.resize", { direction = "left", amount = resize_step })
rex.bind("ctrl+alt+shift+j", "pane.resize", { direction = "down", amount = resize_step })
rex.bind("ctrl+alt+shift+k", "pane.resize", { direction = "up", amount = resize_step })
rex.bind("ctrl+alt+shift+l", "pane.resize", { direction = "right", amount = resize_step })

rex.unbind("alt+shift+cmd+left", "pane.move.left")
rex.unbind("alt+shift+cmd+down", "pane.move.down")
rex.unbind("alt+shift+cmd+up", "pane.move.up")
rex.unbind("alt+shift+cmd+right", "pane.move.right")
rex.bind("ctrl+alt+cmd+h", "pane.move.left")
rex.bind("ctrl+alt+cmd+j", "pane.move.down")
rex.bind("ctrl+alt+cmd+k", "pane.move.up")
rex.bind("ctrl+alt+cmd+l", "pane.move.right")

rex.bind("cmd+shift+k", "client.tab.previous")
rex.bind("cmd+shift+j", "client.tab.next")

rex.action({
	name = "lazygit_popup",
	title = "Open Lazygit Popup",
	run = function()
		local directory = rex.block.call("com.superlogical.terminal", "pwd")
		local cwd = directory and directory.pwd
		if not cwd or cwd == "" then
			local process = rex.block.call("com.superlogical.terminal", "process")
			cwd = process and process.foreground and process.foreground.cwd
		end

		return assert(rex.session.new_layer({
			bounds = { 0.025, 0.025, 0.95, 0.95 },
			focus = true,
			layout = rex.layout.block({
				flavor = "com.superlogical.terminal.shell",
				options = {
					cwd = cwd,
					shell = "none",
					command = { "/bin/zsh", "-lc", "exec lazygit" },
					exit = { on_completion = true },
				},
			}),
		}))
	end,
})

rex.bind("ctrl+space>l", "lazygit_popup")
