# Skill Design Principles

Foundational concepts for designing effective, composable agent skills.

## Core Principles

### 1. Consolidation Principle

Skills should consolidate related capabilities into a single, well-scoped unit rather than spreading functionality across multiple skills.

**Applied to skill creation:**
- Group related workflows together (e.g., all testing scenarios in one skill, not separate skills for each)
- Use references/ folder to organize related documentation without fragmenting into multiple skills
- Each skill should solve a cohesive problem space

**Example**: The webapp-testing skill bundles Playwright-based testing workflows (verification, debugging, screenshots, visual regression) as one consolidated skill rather than separate skills for each capability.

### 2. Progressive Disclosure

Information loading should be minimized at discovery time and expanded progressively as users engage deeper.

**Three-level loading architecture:**
1. **Discovery** (lightweight): Only `name` and `description` loaded by Copilot for skill selection
2. **Instructions** (activated): Full SKILL.md body loads when request matches description keywords
3. **Resources** (on-demand): Scripts, references, and templates load only when Copilot uses them

**Applied to skill structure:**
- Keep SKILL.md main body focused (~500 lines max)
- Move detailed workflows and deep documentation to `references/` folder
- Scripts stay in `scripts/` until explicitly executed
- Users (and Copilot) never load unnecessary content

### 3. Composability

Skills should be designed to work independently AND integrate with other skills when needed.

**Principles:**
- Each skill teaches a complete, self-contained workflow
- Skills reference other skills' principles (e.g., a .NET testing skill references context-fundamentals for context engineering patterns)
- Avoid circular dependencies or redundant overlap
- Clear integration points let users/agents understand when to combine skills

**Applied to agent-skill-creator:**
- This foundational skill teaches principles applicable to all agent skills
- Future tech-specific skills (dotnet-agent-skill, typescript-agent-skill) build on this foundation
- Each can be used independently or together for tech-specific skill creation

### 4. Evaluability

Skills should be designed so their success can be measured and validated.

**Principles:**
- Clear trigger conditions (when the skill should be used)
- Measurable outcomes (what "success" looks like)
- Validation steps integrated into workflows
- Can be tested independently

**Applied to skills:**
- Explicit description keywords ensure skill is activated when relevant
- Step-by-step workflows with expected outputs enable validation
- Referenced documentation provides context for understanding success criteria

## Design Checklist

When creating a skill, ensure:

- [ ] **Consolidation**: All related capabilities included; no unnecessary fragmentation
- [ ] **Progressive Disclosure**: SKILL.md ~500 lines max; detailed content in references/
- [ ] **Composability**: Skill works independently; integration points documented
- [ ] **Evaluability**: Clear triggers, measurable outcomes, validation steps
- [ ] **Description Keywords**: WHAT + WHEN + WHO clearly stated in frontmatter
- [ ] **Resource Bundling**: Scripts, references, templates organized appropriately
- [ ] **Cross-References**: Links to related skills and documentation

## Related Skills

These skills embody these principles:

- **[context-fundamentals](../../context-fundamentals/SKILL.md)** - Progressive disclosure, context engineering patterns
- **[tool-design](../../tool-design/SKILL.md)** - Consolidation principle, architectural reduction
- **[evaluation](../../evaluation/SKILL.md)** - Evaluability, measurement frameworks
- **[advanced-evaluation](../../advanced-evaluation/SKILL.md)** - Composability with evaluation skill

