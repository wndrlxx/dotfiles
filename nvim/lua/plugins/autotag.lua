return {
  {
    "windwp/nvim-ts-autotag",
    ft = { "html", "xml", "javascriptreact", "typescriptreact", "eruby" },
    config = function()
      require("nvim-ts-autotag").setup()
    end,
  },
}
