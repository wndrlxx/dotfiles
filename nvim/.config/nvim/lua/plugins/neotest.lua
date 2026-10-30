return {
  "nvim-neotest/neotest",
  dependencies = {
    "marilari88/neotest-vitest",
    "olimorris/neotest-rspec",
  },
  opts = {
    adapters = {
      "neotest-rspec",
      "neotest-vitest",
    },
  },
}
