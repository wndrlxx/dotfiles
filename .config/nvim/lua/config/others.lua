-- ALE config
vim.g.ale_linters = {
  ruby = {'rubocop'},
  javascript = {'eslint'},
  typescript = {'eslint'},
  go = {'gopls'},
}

vim.g.ale_fixers = {
  ['*'] = {'remove_trailing_lines', 'trim_whitespace'},
  ruby = {'rubocop'},
  javascript = {'prettier'},
  typescript = {'prettier'},
}

vim.g.ale_virtualtext_cursor = 'disabled'
vim.cmd [[
highlight clear ALEWarning
highlight clear ALEError
]]

