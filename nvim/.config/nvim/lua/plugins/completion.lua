return {
  {
    "hrsh7th/nvim-cmp",
    opts = function(_, opts)
      local cmp = require("cmp")
      -- Option + Space opens completion without conflicting with Herdr's prefix.
      opts.mapping["<M-Space>"] = cmp.mapping.complete()
    end,
  },
}
