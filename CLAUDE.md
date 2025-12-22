## Meta-Agent: Automated Codebase Refinement

Meta-agent is a Python CLI tool that analyzes codebases against their PRD and generates prioritized improvement plans. It uses a multi-LLM pipeline for cost-effective, high-quality analysis.

### Pipeline Architecture

Meta-agent has **two main modes** with different architectures:

#### Loop Mode (Primary - `metaagent loop`)
```
┌─────────────────────────────────────────────────────────────────┐
│                     LOOP MODE PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│  1. GROK (xAI) - PRD Parsing                                    │
│     └── Reads PRD and generates prioritized task list           │
│                                                                 │
│  2. CLAUDE (Anthropic) - Implementation                         │
│     └── Implements each task, writes code changes               │
│                                                                 │
│  3. TEST RUNNER                                                 │
│     └── Runs pytest (or custom test command) after each change  │
│                                                                 │
│  4. GROK - Error Diagnosis (if tests fail)                      │
│     └── Analyzes failures, suggests fixes                       │
│                                                                 │
│  5. GROK - Final Evaluation                                     │
│     └── Checks PRD alignment, generates completion report       │
└─────────────────────────────────────────────────────────────────┘
```

#### Refine Mode (Analysis - `metaagent refine --smart`)
```
┌─────────────────────────────────────────────────────────────────┐
│                     REFINE MODE PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│  1. REPOMIX - Pack codebase into single file                    │
│  2. OLLAMA (local) - Triage: select relevant files/prompts      │
│  3. PERPLEXITY - Analysis with reduced context                  │
│  4. PLAN WRITER - Generate mvp_improvement_plan.md              │
└─────────────────────────────────────────────────────────────────┘
```

**Which to use?**
- **`loop`**: For autonomous implementation (PRD → working code)
- **`refine --smart`**: For analysis only (generates improvement plan)

### Refinement Modes

#### 1. Profile-Based Mode (Simple)
```bash
metaagent refine --profile automation_agent
```
Runs predefined analysis stages from `config/profiles.yaml`. Deterministic, no triage.

#### 2. Smart Mode with Ollama Triage
```bash
metaagent refine --smart
```
- Ollama analyzes full codebase against PRD
- Selects which prompts to run
- Sends only relevant files to Perplexity

#### 3. Feature-Focused Mode (Recommended)
```bash
metaagent refine --smart --focus "add user authentication"
```
- Ollama selects relevant FILES for the feature
- Perplexity receives reduced context + prompt library
- Perplexity selects AND rewrites prompts for your specific feature
- Best for adding specific features

#### 4. Iterative Loop Mode (Full Automation)
```bash
metaagent refine --smart --focus "add user authentication" --loop
```
- Runs feature-focused mode in a loop
- After each iteration: analyze → implement → commit → repeat
- Continues until feature is complete or max iterations reached
- Use `--max-iterations 10` to limit

#### 5. Auto-Implement Mode
```bash
metaagent refine --smart --focus "feature" --auto-implement
```
- Automatically runs Claude Code to implement recommended changes
- Commits changes after implementation

#### 6. Grok-Powered Local Loop (NEW)
```bash
metaagent refine --local-loop docs/prd.md
```
- Uses **Grok (xAI)** as the primary evaluator instead of Perplexity
- Works directly in current repository (local-first, no workspace isolation)
- Uses **GitPython** for safer git operations
- Cycle: Analyze → Implement (Claude) → Test → Diagnose errors (Grok) → Fix → Commit
- Final Grok evaluation for PRD alignment

```bash
# Basic local loop
metaagent refine --local-loop docs/prd.md

# With options
metaagent refine --local-loop docs/prd.md --max-iterations 15 --human-approve

# Use Perplexity instead of Grok
metaagent refine --local-loop docs/prd.md --evaluator perplexity

# Dry-run mode (no commits)
metaagent refine --local-loop docs/prd.md --dry-run
```

### Essential Commands

```bash
# PRIMARY: Autonomous task loop (Grok + Claude)
metaagent loop --prd docs/prd.md                    # Run with human approval
metaagent loop --prd docs/prd.md --no-human-approve # Fully autonomous
metaagent loop --prd docs/prd.md --dry-run          # Preview without changes

# Launch GUI (no terminal needed)
metaagent --gui

# Analysis only (no implementation)
metaagent refine --profile automation_agent         # Profile-based
metaagent refine --smart                            # Ollama triage mode
metaagent refine --smart --focus "your feature"     # Feature-focused

# List available profiles/prompts
metaagent list-profiles
metaagent list-prompts

# Launch real-time dashboard
metaagent dashboard
```

### Configuration

#### Environment Variables (`.env`)
```bash
PERPLEXITY_API_KEY=pplx-xxx   # Required for analysis (or use --mock)
ANTHROPIC_API_KEY=sk-ant-xxx  # Optional - for Claude integration
GROK_API_KEY=xai-xxx          # Required for --local-loop mode (xAI)
METAAGENT_TIMEOUT=120         # Request timeout
METAAGENT_MAX_TOKENS=100000   # Max tokens per request
```

#### Prerequisites
- Python 3.10+
- Repomix: `npm install -g repomix`
- Ollama: Must be installed and running for `--smart` mode
- Perplexity API key: Required for paid analysis

### Project Structure

```
meta-agent/
├── src/metaagent/
│   ├── cli.py           # CLI entrypoint
│   ├── orchestrator.py  # Pipeline orchestration (smart mode, triage, local loop)
│   ├── ollama_engine.py # Ollama integration for local triage
│   ├── analysis.py      # Perplexity/LLM analysis engine
│   ├── grok_client.py   # Grok API client for error diagnosis (NEW)
│   ├── local_manager.py # GitPython-based repo manager (NEW)
│   ├── repomix.py       # Codebase packing
│   ├── plan_writer.py   # Plan file generation
│   └── claude_runner.py # Claude Code integration
├── config/
│   ├── prompts.yaml     # Custom prompt templates
│   ├── profiles.yaml    # Profile definitions (stages)
│   ├── loop_config.yaml # Loop mode configuration
│   └── prompt_library/  # Codebase-digest prompts
└── docs/
    └── prd.md           # Project PRD
```

### Output

After running, meta-agent generates:
- `docs/mvp_improvement_plan.md`: Human-readable improvement plan
- Console output: Implementation report with prioritized tasks
- The current Claude Code session receives structured tasks to implement

### Workflow Integration

1. **Write PRD**: Create `docs/prd.md` describing your feature/project
2. **Run Meta-Agent**: `metaagent refine --smart --focus "feature"`
3. **Review Plan**: Check generated `docs/mvp_improvement_plan.md`
4. **Implement**: Work through tasks (or use `--auto-implement`)
5. **Iterate**: Re-run to find remaining gaps

### Available Profiles

| Profile | Description |
|---------|-------------|
| `automation_agent` | For CLI tools and automation |
| `backend_service` | APIs with security review |
| `internal_tool` | Lighter analysis |
| `quick_review` | PRD alignment only |
| `full_review` | Comprehensive analysis |

### Tips

- **Use `--smart --focus` for new features**: Most effective mode
- **Use `--loop` for complex features**: Automated iteration
- **Use `--local-loop` for Grok-powered development**: Works directly in your repo
- **Always have a PRD**: Meta-agent works best with clear requirements
- **Check Ollama status**: Run `ollama list` to ensure models are available
- **Start with `--mock` or `--dry-run`**: Test your workflow without API costs

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
