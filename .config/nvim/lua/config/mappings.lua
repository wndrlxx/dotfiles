-- Keymaps
vim.keymap.set("n", "<leader>n", ":NvimTreeToggle<CR>")
vim.keymap.set("n", "<leader>vn", ":NvimTreeFindFile<CR>")

vim.keymap.set("n", "C-h", ':TmuxNavigateLeft<CR>')
vim.keymap.set("n", "C-j", ':TmuxNavigateDown<CR>')
vim.keymap.set("n", "C-k", ':TmuxNavigateUp<CR>')
vim.keymap.set("n", "C-l", ':TmuxNavigateRight<CR>')

vim.api.nvim_set_keymap('n', '<Leader>f', ':FZF<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>r', ':Rg<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>e', ':RunReek<CR>', { noremap = true, silent = true })

vim.api.nvim_set_keymap('n', '<Leader>w', ':w<CR>', { noremap = true })
vim.api.nvim_set_keymap('n', '<Leader>q', ':q<CR>', { noremap = true })

vim.api.nvim_set_keymap('n', '<Leader>t', ':TestNearest<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>T', ':TestFile<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<Leader>a', ':TestSuite<CR>', { noremap = true, silent = true })

vim.api.nvim_set_keymap('i', 'jk', '<Esc>', { noremap = true })

