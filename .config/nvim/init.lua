-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")
-- ensure Neovim sees Homebrew binaries first
vim.env.PATH = "/opt/homebrew/bin:" .. vim.env.PATH
