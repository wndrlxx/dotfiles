-- Escape from insert mode using 'jk'
vim.keymap.set("i", "jk", "<Esc>", { noremap = true, silent = true })

-- Toggle Copilot autocomplete
vim.keymap.set("n", "<leader>a", function()
  local client = require("copilot.client")
  local command = require("copilot.command")
  if client.is_disabled() then
    command.enable()
  else
    command.disable()
  end
  vim.notify("Copilot " .. (client.is_disabled() and "disabled" or "enabled"))
end, { desc = "Toggle Copilot autocomplete" })
