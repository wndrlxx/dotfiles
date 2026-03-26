return {
  "nvim-neotest/neotest",
  lazy = true,
  dependencies = {
    "marilari88/neotest-vitest",
    "olimorris/neotest-rspec", -- make sure you install the correct rspec adapter plugin
  },
  config = function()
    require("neotest").setup({
      -- add any global opts here
      adapters = {
        require("neotest-rspec"),
        require("neotest-vitest"),
      },
    })
  end,
}
