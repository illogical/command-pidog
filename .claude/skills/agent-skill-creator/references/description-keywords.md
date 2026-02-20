# Description Keywords & Activation Triggers

The skill `description` field is the PRIMARY mechanism for Copilot to discover and activate skills. This guide ensures your description enables proper activation.

## Why Description Matters

Copilot uses a two-stage loading process:

1. **Discovery Stage** (Always happens): Copilot reads ONLY `name` and `description` to decide whether to load your skill
2. **Instruction Stage** (If activated): Copilot loads the full SKILL.md body only if the description matched the user's request

**If your description is vague, your skill is never activated.**

## The Description Formula

Effective descriptions follow this structure:

```
[CAPABILITY] for [DOMAIN/USE-CASE]. Use when [TRIGGER 1], [TRIGGER 2], or [TRIGGER 3]. [OPTIONAL: What it supports/enables].
```

## Components

### 1. CAPABILITY (What)
**What your skill does in 1-2 sentences**

```
✅ GOOD                                              ❌ POOR
"Toolkit for testing web applications"              "Web testing helpers"
"Generator for .NET project scaffolds"              "Project generator"
```

**Guidelines:**
- Start with noun + verb: "Toolkit for...", "Generator for...", "Framework for..."
- Be specific about the domain: "web applications", "Agent Skills", ".NET projects"
- Not vague ("toolkit", "helper")

### 2. DOMAIN/USE-CASE (Where)
**The context where this skill applies**

Examples:
- Testing local web applications
- Creating .NET agent skills
- Evaluating AI agent outputs
- Managing agent context windows

```
✅ Skill: webapp-testing (Domain: testing local web applications)
✅ Skill: dotnet-agent-skill (Domain: creating .NET-specific skills)
✅ Skill: evaluation (Domain: evaluating AI agent outputs)
```

### 3. TRIGGER PHRASES (When)
**Specific user requests that should activate this skill**

Include 3-4 trigger phrases covering different ways users might ask for this capability.

#### Trigger Categories

| Category | Purpose | Example Triggers |
|---|---|---|
| **Action-based** | User wants to perform a specific action | "verify frontend functionality", "debug UI behavior", "generate a new skill" |
| **Keyword-based** | User mentions specific tools, frameworks, formats | "Playwright", "xUnit", "YAML", ".NET" |
| **File-type based** | User shows/mentions specific file extensions | ".jsx files", ".cs files", ".py scripts" |
| **Scenario-based** | User describes a situation | "testing a web app", "writing an evaluation rubric" |
| **Problem-based** | User describes a problem to solve | "visual regression detection", "context window exhaustion" |

#### Example: webapp-testing

**What**: Playwright-based testing toolkit
**When triggers:**
- "verify frontend functionality" (Action)
- "Playwright, Chrome, Firefox" (Keyword)
- ".html, .jsx, .tsx files" (File-type)
- "debug UI behavior, capture screenshots" (Scenario)
- "visual regression detection" (Problem)

```yaml
description: Toolkit for testing local web applications using Playwright. Use when asked to verify frontend functionality, debug UI behavior, capture browser screenshots, check for visual regressions, or view browser console logs. Supports Chrome, Firefox, and WebKit browsers.
```

#### Example: agent-skill-creator

**What**: Tool for creating new agent skills
**When triggers:**
- "create a new skill" (Action)
- "YAML frontmatter, SKILL.md" (Keyword)
- ".github/skills/, .claude/skills/" (File-type/location)
- "portable skill, bundled resources" (Scenario)
- "activate agent workflows" (Problem/purpose)

```yaml
description: Creates new agent skills following modern best practices with proper structure and documentation. Use when asked to build a new skill, organize skill resources, design skill descriptions, or validate skill structure for portability across Copilot platforms.
```

### 4. OPTIONAL: Supported Details
**What platforms/frameworks/variants this skill supports**

```
✅ "Supports Chrome, Firefox, and WebKit browsers"
✅ "Works with async/await, callbacks, and promises"
✅ "Handles xUnit, NUnit, and MSTest frameworks"
```

## Writing Strong Descriptions

### Start Specific

```
✅ "Generator for creating .NET projects following best practices"
❌ "Creates projects"

✅ "Playwright-based testing for web applications"
❌ "Testing toolkit"

✅ "Framework for designing composable, evaluable AI agent skills"
❌ "Skill creation helper"
```

### Include Activation Keywords

Map user language to your skill:

```
If your skill handles...        Include these keywords...
Testing web UIs                 "Playwright", "browser", "UI", "screenshot", "visual"
Evaluating AI output            "rubric", "scoring", "evaluation", "quality", "measurement"
Creating agent skills           "SKILL.md", "portable", "resources", "bundling"
Async operations                "async/await", "concurrency", "parallel", "streaming"
```

### Cover Multiple Scenarios

Users ask in different ways. Cover them:

```
Scenario 1: "I need to test this web app"           ← Action-based trigger
Scenario 2: "How do I use Playwright?"              ← Tool-based trigger
Scenario 3: "Check this .jsx file for UI bugs"      ← File-based trigger
Scenario 4: "I want visual regression detection"    ← Problem-based trigger

All should activate the same skill.
Description must include keywords from all scenarios.
```

## Anti-Patterns

### Vague descriptions (Don't do this)

```yaml
❌ "Testing utilities"           # What kind? When? Why?
❌ "Helper toolkit"              # For what?
❌ "Code generation"             # For what domain?
❌ "Best practices guide"        # For which domain?
```

**Why they fail**: Copilot can't match user requests to vague descriptions.

### Keyword stuffing (Don't do this)

```yaml
❌ "testing playwright browser chrome firefox ui debug
   evaluate quality score rubric assessment framework..."
```

**Why it fails**: Incoherent, hard to parse, actually confuses activation matching.

### Too narrow (Don't do this)

```yaml
❌ "Run Playwright tests on localhost:3000 with Chrome browser"
```

**Why it fails**: Only matches one specific scenario; misses related requests.

### Too long (Don't do this)

```yaml
❌ "This is a comprehensive guide to using Playwright for web testing, including 
   browser automation, visual regression detection, screenshot capture, console log 
   viewing, and integration with CI/CD systems. It works with Chrome, Firefox, and 
   WebKit. It handles both headless and headful modes..."
```

**Why it fails**: Exceeds 1024 character limit; loses clarity; violates constraint.

## Testing Your Description

Before finalizing, ask:

- [ ] **Is it specific?** Does it clearly state what the skill does (not just "helper" or "toolkit")?
- [ ] **Does it cover WHEN?** Would a user recognize this skill matches their request?
- [ ] **Does it include keywords?** Specific tool names, frameworks, file types they'd mention?
- [ ] **Is it under 1024 characters?** Keep focused and scannable.
- [ ] **Does it pass the hypothetical test?**
  - User: "I need to test my web app in the browser"
  - Would your description match? ✅ YES for webapp-testing skill
  
## Examples by Domain

### Testing Domain
```yaml
description: Toolkit for testing local web applications using Playwright. Use when asked to verify frontend functionality, debug UI behavior, capture browser screenshots, check for visual regressions, or view browser console logs. Supports Chrome, Firefox, and WebKit browsers.
```

### Skill Creation Domain
```yaml
description: Creates new agent skills following modern best practices with proper structure and documentation. Use when asked to build a new skill, organize skill resources, design skill descriptions, or validate skill structure for portability across Copilot platforms.
```

### .NET Development Domain (Future)
```yaml
description: Creates .NET agent skills following C# and .NET best practices. Use when building skills for .NET/C# contexts, need MSBuild guidance, testing in xUnit/NUnit, dependency injection patterns, or ASP.NET Core integration. Builds on agent-skill-creator foundations.
```

### TypeScript Development Domain (Future)
```yaml
description: Creates TypeScript agent skills following Node.js and modern JavaScript best practices. Use when building skills for TypeScript/JavaScript contexts, need bundling configuration, testing frameworks, or async patterns. Supports ESM modules. Builds on agent-skill-creator foundations.
```

## Related Guidance

- [Agent Skills File Guidelines - Description Best Practices](../../../instructions/agent-skills.instructions.md#description-best-practices)
- [Skill Design Principles](./skill-design-principles.md)

