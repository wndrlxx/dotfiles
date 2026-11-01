return {
  {
    "folke/snacks.nvim",
    keys = {
      { "<leader><space>", LazyVim.pick("files", { root = false }), desc = "Find Files (cwd)" },
    },
    opts = function(_, opts)
      opts.indent = opts.indent or {}
      opts.indent.enabled = false
      opts.picker = vim.tbl_deep_extend("force", opts.picker or {}, {
        win = {
          input = {
            keys = {
              ["H"] = { "toggle_hidden", mode = "n" },
            },
          },
          list = {
            keys = {
              ["H"] = { "toggle_hidden", mode = "n" },
            },
          },
        },
      })
    end,
  },
}
