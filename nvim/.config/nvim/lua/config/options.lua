-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here
vim.opt.clipboard = "unnamedplus"
vim.opt.swapfile = false
local handle = io.popen("defaults read -g AppleInterfaceStyle 2>/dev/null")
local result = handle:read("*a")
handle:close()
vim.opt.background = result:match("Dark") and "dark" or "light"
