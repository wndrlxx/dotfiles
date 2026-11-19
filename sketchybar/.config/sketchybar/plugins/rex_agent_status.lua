-- Publish read-only snapshots to the SketchyBar agent status watcher.
local terminal = "com.superlogical.terminal"
local sessions = {}
local apps = { codex = "Codex", pi = "Pi" }
local visible = { working = true, blocked = true, done = true, error = true }

local function read_block(session_id, block_id, label)
  local target = { session_id = session_id, block_id = block_id }
  local report = rex.block.call(terminal, "program_status", target)
  local agents = {}
  for _, record in ipairs(report and report.records or {}) do
    local app = apps[record.app]
    if app and visible[record.state] then
      local name = record.title
      if (not name or name == "") and (not label or label == "") then
        local title = rex.block.call(terminal, "title", target)
        label = title and title.title or app
      end
      local id = "rex:" .. block_id .. "/" .. (record.id or "")
      agents[id] = {
        pane_id = id,
        agent = record.app,
        agent_status = record.state,
        name = name ~= nil and name ~= "" and name or label,
        source = "Rex",
      }
    end
  end
  return agents
end

local function refresh_session(session_id)
  local snapshot = rex.session.list_blocks{ session_id = session_id }
  local blocks = {}
  for _, block in ipairs(snapshot and snapshot.blocks or {}) do
    if block.creator_name == terminal then
      blocks[block.block_id] = {
        label = block.label,
        agents = read_block(session_id, block.block_id, block.label),
      }
    end
  end
  sessions[session_id] = blocks
end

local function emit()
  local agents = {}
  for _, blocks in pairs(sessions) do
    for _, block in pairs(blocks) do
      for id, agent in pairs(block.agents) do
        agents[id] = agent
      end
    end
  end
  print(assert(rex.json.encode(agents)))
end

local function refresh_block(ctx)
  local blocks = sessions[ctx.session_id]
  local block = blocks and blocks[ctx.block_id]
  if block then
    block.agents = read_block(ctx.session_id, ctx.block_id, block.label)
  else
    refresh_session(ctx.session_id)
  end
  emit()
end

if not rex.args.snapshot then
  rex.on("terminal.program_status_changed", refresh_block)
  rex.on("terminal.program_status_removed", refresh_block)
  for _, event in ipairs({ "block_created", "block_closed", "window_closed" }) do
    rex.on(event, function(ctx)
      refresh_session(ctx.session_id)
      emit()
    end)
  end
  rex.on("session_created", function(_, event)
    refresh_session(event.session.session_id)
    emit()
  end)
  rex.on("session_destroyed", function(_, event)
    sessions[event.session_id] = nil
    emit()
  end)
end

-- Subscribe before reading so events during initialization can refresh the snapshot.
local snapshot = assert(rex.call("session.attach_all", { event_scope = "all" }))
for _, session in ipairs(snapshot.sessions) do
  refresh_session(session.session_id)
end
emit()
