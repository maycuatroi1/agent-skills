---
name: gitnexus
description: Retired on 2026-11-12. GitNexus is no longer used, so do not install, index or call it; code intelligence goes through evo-kg (the kg_* tools).
disable-model-invocation: true
version: 0.2.0
---

# gitnexus (retired)

GitNexus was retired on 2026-11-12, for `rename` and taint analysis as well. Its MCP server is no longer configured, and nothing in the evo clusters calls it.

- Look up code, measure blast radius and check a change with evo-kg: `kg_search`, `kg_context`, `kg_impact`.
- For a rename, run `kg_impact` on the symbol, then grep for what its coverage note says the graph misses.
- Do not run `scripts/install.sh` or `scripts/index-workspace.sh`: they put the GitNexus MCP server and its hooks back.

The old instructions are version 0.1.0 of this file in the git history of agent-skills (hub skill `gitnexus`, version 1).
