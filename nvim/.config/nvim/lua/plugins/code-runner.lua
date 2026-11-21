local run_in_rex_float = [[
  assert(rex.session.new_layer({
    bounds = { 0.10, 0.10, 0.80, 0.80 },
    focus = true,
    layout = rex.layout.block({
      flavor = "com.superlogical.terminal.shell",
      options = {
        cwd = rex.args.cwd,
        shell = "none",
        command = { rex.args.shell, "-lic", rex.args.command },
        exit = { on_completion = false },
      },
    }),
  }))
]]

local function package_manager(path)
  local ok, manifest = pcall(function()
    return vim.json.decode(table.concat(vim.fn.readfile(path), "\n"))
  end)
  if ok and type(manifest) == "table" and type(manifest.packageManager) == "string" then
    return manifest.packageManager:match("^([^@]+)@")
  end
end

local function typescript_command()
  local file = vim.api.nvim_buf_get_name(0)
  local node_project = false
  local runtime

  for dir in vim.fs.parents(file) do
    local function has(name)
      return vim.fn.filereadable(vim.fs.joinpath(dir, name)) == 1
    end

    if has("deno.json") or has("deno.jsonc") or has("deno.lock") then
      runtime = "deno run"
      break
    end

    local manager
    if has("package.json") then
      node_project = true
      manager = package_manager(vim.fs.joinpath(dir, "package.json"))
    end
    if manager == "bun" or has("bun.lock") or has("bun.lockb") or has("bunfig.toml") then
      runtime = "bun run"
      break
    end
    if
      manager == "npm"
      or manager == "pnpm"
      or manager == "yarn"
      or has("package-lock.json")
      or has("pnpm-lock.yaml")
      or has("yarn.lock")
    then
      node_project = true
      break
    end
    if vim.uv.fs_stat(vim.fs.joinpath(dir, ".git")) then
      break
    end
  end

  if not runtime and node_project then
    runtime = "node"
    for dir in vim.fs.parents(file) do
      if vim.fn.filereadable(vim.fs.joinpath(dir, "node_modules/tsx/package.json")) == 1 then
        runtime = "node --import=tsx"
        break
      end
      if vim.uv.fs_stat(vim.fs.joinpath(dir, ".git")) then
        break
      end
    end
  end
  return "cd $dir && " .. (runtime or "deno run") .. " $file"
end

local function run_current_file()
  vim.cmd.update()
  if not vim.env.REX_SESSION then
    vim.cmd.RunFile()
    return
  end

  local rex = vim.env.REX_BIN_DIR and vim.fs.joinpath(vim.env.REX_BIN_DIR, "rex") or "rex"
  if vim.fn.executable(rex) ~= 1 then
    vim.notify("Rex CLI executable was not found", vim.log.levels.ERROR)
    return
  end

  local command = require("code_runner").get_filetype_command()
  if command == "" then
    vim.cmd.RunFile()
    return
  end

  local args = vim.json.encode({ cwd = vim.fn.getcwd(), shell = vim.o.shell, command = command })
  vim.system(
    { rex, "do", "-e", run_in_rex_float, "--args", args },
    { text = true },
    vim.schedule_wrap(function(result)
      if result.code ~= 0 then
        local message = vim.trim(result.stderr or "")
        vim.notify(message ~= "" and message or "Rex could not open a floating window", vim.log.levels.ERROR)
      end
    end)
  )
end

return {
  "CRAG666/code_runner.nvim",
  cmd = "RunFile",
  keys = {
    { "<leader>rf", run_current_file, desc = "Run current file" },
  },
  opts = {
    mode = "float",
    float = {
      close_key = "q",
    },
    filetype = {
      ruby = "ruby",
      -- -u to show progress as it is printed
      python = "python3 -u",
      javascript = "node",
      typescript = typescript_command,
    },
  },
}
