-- return {
--   "neovim/nvim-lspconfig",
--   lazy = false,
--   config = function()
--     local capabilities = require("cmp_nvim_lsp").default_capabilities()
--
--     local lspconfig = require("lspconfig")
--     lspconfig.ruby_lsp.setup({
--       capabilities = capabilities,
--     })
--
--     vim.keymap.set("n", "K", vim.lsp.buf.hover, {})
--     vim.keymap.set("n", "<leader>ce", vim.lsp.buf.definition, { desc = "Goto definition" })
--     vim.keymap.set("n", "<leader>cr", vim.lsp.buf.references, { desc = "References" })
--     vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, { desc = "Code Action" })
--     vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, { desc = "Rename" })
--   end,
-- }
--

return {
  -- 1. Updated Mason organization name
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      vim.list_extend(opts.ensure_installed, { "astro-language-server", "emmet-language-server" })
    end,
  },

  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        ruby_lsp = {},
        astro = {}, -- Astro LSP
        emmet_language_server = {
          filetypes = {
            "astro",
            "css",
            "eruby",
            "html",
            "javascript",
            "javascriptreact",
            "less",
            "sass",
            "scss",
            "pug",
            "typescriptreact",
          },
        },
      },
    },
    -- 2. Your custom keymaps
    keys = {
      { "K", vim.lsp.buf.hover, desc = "Hover" },
      { "<leader>ce", vim.lsp.buf.definition, desc = "Goto definition" },
      { "<leader>cr", vim.lsp.buf.references, desc = "References" },
      { "<leader>ca", vim.lsp.buf.code_action, desc = "Code Action" },
      { "<leader>rn", vim.lsp.buf.rename, desc = "Rename" },
    },
  },

  -- 3. Astro Syntax Highlighting
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      if type(opts.ensure_installed) == "table" then
        vim.list_extend(opts.ensure_installed, { "astro" })
      end
    end,
  },
}
