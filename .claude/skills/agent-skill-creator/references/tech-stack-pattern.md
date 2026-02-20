# Tech-Stack Extension Pattern

Pattern for creating tech-specific agent skills that build on the foundational agent-skill-creator skill.

## Overview

Rather than embedding tech-specific guidance in the foundational skill, the extension pattern keeps agent-skill-creator focused on universal principles while allowing tech-specific skills to layer tech-relevant context and best practices on top.

This maintains modularity:
- Users creating .NET agent skills reference both agent-skill-creator (foundational) + dotnet-agent-skill (specific)
- Users creating TypeScript skills reference both agent-skill-creator (foundational) + typescript-agent-skill (specific)
- Each tech-specific skill inherits the universal principles and adds tech-specific patterns

## Tech-Specific Skill Pattern

### Naming Convention

**Format**: `{tech}-agent-skill`

**Examples:**
- `dotnet-agent-skill` - Foundational skill for creating .NET-focused agent skills
- `typescript-agent-skill` - Foundational skill for creating TypeScript/Node.js-focused agent skills
- `python-agent-skill` - Foundational skill for creating Python-focused agent skills

### Directory Structure

```
.github/skills/dotnet-agent-skill/
├── SKILL.md
├── LICENSE.txt
├── references/
│   ├── dotnet-project-structures.md      # .NET project layouts, conventions
│   ├── dotnet-best-practices.md          # C#, MSBuild, testing patterns
│   └── dotnet-skill-patterns.md          # How to create .NET agent skills specifically
└── scripts/
    └── dotnet-skill-scaffolder.py        # Automated scaffolding for .NET skills
```

### Frontmatter Example

```yaml
---
name: dotnet-agent-skill
description: Creates .NET agent skills following C# and .NET best practices. Use when building skills for .NET/C# contexts, need MSBuild guidance, testing in xUnit/NUnit, dependency injection patterns, or ASP.NET Core integration. Builds on agent-skill-creator foundations.
---
```

**Key elements:**
- Name follows `{tech}-agent-skill` convention
- Description references that it **builds on agent-skill-creator**
- Includes .NET-specific keywords (C#, MSBuild, xUnit, NUnit, dependency injection, ASP.NET)
- Clear scenarios when to use this tech-specific skill

### Body Structure

```markdown
# {Tech} Agent Skills

When creating agent skills for {Tech} contexts, follow [agent-skill-creator](../agent-skill-creator/SKILL.md) foundational principles with these {Tech}-specific enhancements.

## {Tech}-Specific Principles

- Key principle 1: ...
- Key principle 2: ...
- Key principle 3: ...

See [skill design principles](./skill-design-principles.md) for foundational concepts.

## Project Structure Patterns

[{Tech} project structures](./references/dotnet-project-structures.md) outlines standard organization for {Tech} projects. When creating skills, assume these structures and reference them in documentation.

## Testing & Validation

[{Tech} testing patterns](./references/dotnet-best-practices.md#testing) documents test frameworks, validation approaches, and common testing scenarios in {Tech}.

## Creating {Tech} Skills: Step-by-Step

### 1. Define Scope
Same as [agent-skill-creator step 1](../agent-skill-creator/SKILL.md#step-1-define-scope), but apply {Tech}-specific keyword filtering:
- Include {Tech}-specific triggers in description (e.g., file extensions: `.cs`, `.csproj`)
- Reference {Tech} tools and frameworks in capabilities

### 2. Design Description with {Tech} Keywords
See [description keywords guide](./description-keywords.md) with these {Tech} specifics:
- Keywords: C#, MSBuild, xUnit, async/await, dependency injection, etc.
- Triggers: When user mentions .NET files, ASP.NET, C# patterns, etc.

### 3-6. Follow Foundational Process
Steps 3-6 are identical to [agent-skill-creator](../agent-skill-creator/SKILL.md#step-3-create-directory-structure). No tech-specific variation needed.

## {Tech}-Specific Resource Bundling

See [resource bundling strategy](./resource-bundling-strategy.md) with these {Tech} recommendations:

| Resource Type | {Tech} Example | Purpose |
|--------------|---|---------|
| scripts/ | [dotnet-skill-scaffolder.py](./scripts/dotnet-skill-scaffolder.py) | Auto-generate {Tech} skill boilerplate |
| references/ | [dotnet-project-structures.md](./references/dotnet-project-structures.md) | {Tech}-specific directory layouts |
| templates/ | Sample .csproj, Program.cs | {Tech}-specific starter code |

## References

- [Foundational agent-skill-creator](../agent-skill-creator/SKILL.md)
- [{Tech} Best Practices](./references/dotnet-best-practices.md)
- [{Tech} Project Structures](./references/dotnet-project-structures.md)
```

## Implementation Timeline

This pattern enables incremental implementation:

1. **Phase 1** (Now): Complete agent-skill-creator as foundational skill
2. **Phase 2** (Q1 2026): Create dotnet-agent-skill using this pattern
3. **Phase 3** (Q2 2026): Create typescript-agent-skill using this pattern
4. **Phase 4** (Q3+ 2026): Python, Rust, Go, etc. skills follow same pattern

Each phase layer-builds on previous work without duplicating foundational principles.

## Cross-Referencing in Future Skills

When tech-specific skills reference agent-skill-creator:

**In SKILL.md:**
```markdown
Follow [foundational skill creation principles](../agent-skill-creator/SKILL.md) with these .NET-specific enhancements.
```

**In references/ docs:**
```markdown
See [skill design principles](./skill-design-principles.md#consolidation-principle) for why this pattern uses consolidation.
```

**In descriptions:**
```yaml
description: Creates .NET agent skills following agent-skill-creator principles with C#/.NET specifics...
```

This creates a clear hierarchy:
- **agent-skill-creator**: Universal (all skills)
- **{tech}-agent-skill**: Specific (tech-focused)
- **domain-specific skills**: Very specific (e.g., "asp-net-core-testing" that uses both dotnet-agent-skill + testing patterns)

