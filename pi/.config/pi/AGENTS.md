# Formatting

After creating or editing code files:

- Run the formatter configured by the project on the changed files.
- For Bash scripts, use shfmt. Follow .editorconfig when present; otherwise use `shfmt -i 2 -w <files>`.
- Format only files changed during this task, not the entire repository.
- Avoid unrelated formatting changes.
- If the formatter is missing or fails, report that clearly.
- Do not install formatters or change formatter configuration without asking.

# Commit messages

Use Conventional Commits style: `type(scope): description`. Keep messages concise
and easy for people to understand, using plain language and imperative verbs.
Favor clarity over brevity. When useful, add a short bullet-point body explaining
the changes.
