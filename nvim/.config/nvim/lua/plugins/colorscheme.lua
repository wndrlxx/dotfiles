return {
  {
    "LazyVim/LazyVim",
    opts = function()
      local is_dark = vim.o.background == "dark"
      return {
        colorscheme = is_dark and "tokyonight" or "rose-pine",
      }
    end,
  },

  -- Tokyo Night (dark theme)
  {
    "folke/tokyonight.nvim",
    name = "tokyonight",
    opts = {
      style = "night", -- default dark style
      transparent = true,
    },
  },

  -- Rose Pine (light theme)
  {
    "rose-pine/neovim",
    name = "rose-pine",
    opts = {
      variant = "dawn",
      disable_background = false,
    },
  },
}
