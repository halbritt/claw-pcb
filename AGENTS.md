# AGENTS.md

🦞 Claw Board — a real Altium PCB designed entirely in Python via
[altium-monkey](https://github.com/wavenumber-eng/altium_monkey). See
[`README.md`](README.md) for project detail.

## Operators: start here

**If you've been named an operator** — i.e. you are driving striatum workflows
against this repository, not just editing its files — do not improvise a cold
start. Run the striatum operator initialization first:

```bash
striatum operator bootstrap --markdown
```

Then follow the returned `next_actions` and bounded `reading_plan` before
opening broad repository docs. Use `--json` instead of `--markdown` when another
tool will consume the packet. This needs the striatum daemon running and this
repository registered as a striatum target.

If you are already inside a supervised lane holding a work packet, that packet
and the installed RFC 0015 skill bundle (`.claude/skills/striatum-*/`,
`.codex/agents/striatum-*.md`, `.agy/skills/striatum-*/`, or
`striatum-STRIATUM_AGENT_GUIDE.md`) are authoritative — prefer their command
shapes over anything here. The long-form companion is
`docs/how-to/how-to-agent.md` in the striatum repo.
