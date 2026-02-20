# Resource Bundling Strategy

When and how to include scripts, references, templates, and assets in your agent skill.

## Resource Types & When to Use

| Resource | Purpose | Use When | Load Strategy |
|----------|---------|----------|---|
| **SKILL.md** | Main instructions | Always required | Full body on activation |
| **scripts/** | Executable automation | Code is reused, complex, or stability-critical | On-demand execution |
| **references/** | Deep documentation | Content exceeds 500 lines or is optional reading | On-demand reading |
| **templates/** | Starter code the agent modifies | Boilerplate is complex or requires consistency | On-demand customization |
| **assets/** | Static output files | Content used unchanged in user output | On-demand inclusion |

See [Agent Skills File Guidelines - Resource Types](../../../instructions/agent-skills.instructions.md#supported-resource-types) for detailed definitions.

## Decision Framework

### Should I Create a Script?

**Create scripts/ when:**
- ✅ The same code would be regenerated repeatedly by the agent
- ✅ The operation is complex (>100 lines of logic)
- ✅ Deterministic behavior is critical (file ops, API calls, validation)
- ✅ The code evolves independently (version updates, bug fixes)
- ✅ Testability matters (can unit test before deployment)
- ✅ The operation has a clear, self-contained purpose

**Example**: The [webapp-testing](../../webapp-testing/) skill includes [test-helper.js](../../webapp-testing/test-helper.js) because:
- Playwright setup is complex and repeated across test scenarios
- Browser interaction logic is deterministic and testable
- Users shouldn't regenerate this each request

**Don't create scripts when:**
- ❌ The code is simple (< 20 lines of logic)
- ❌ It's a one-time operation
- ❌ The agent needs dynamic customization each invocation
- ❌ Security requires fresh code generation (credential handling)

### Should I Create References?

**Create references/ when:**
- ✅ Documentation exceeds 500 lines
- ✅ Users should read it conditionally (optional deep dives)
- ✅ Multiple workflows reference the same documentation
- ✅ Content is rarely changed (specifications, standards)
- ✅ The main SKILL.md should stay focused on workflow

**Example**: [tool-design](../../tool-design/) skill includes these references:
- [best_practices.md](../../tool-design/references/best_practices.md) - 600+ lines on consolidation principle
- [architectural_reduction.md](../../tool-design/references/architectural_reduction.md) - Deep theory on tool consolidation

SKILL.md stays focused on workflow with links to these deep dives.

**Don't create references when:**
- ❌ Content is <300 lines
- ❌ Every user needs to read it (keep in SKILL.md)
- ❌ It's a quick reference (parameter table is fine in SKILL.md)

### Should I Create Templates?

**Create templates/ when:**
- ✅ Starter code is complex or verbose (>50 lines)
- ✅ Users frequently need to customize the same boilerplate
- ✅ The template embeds best practices users should follow
- ✅ Consistency matters across multiple user implementations

**Example**: [project-development](../../project-development/) skill should include:
- Pipeline scaffold template (.py file with step structure)
- Configuration template (settings users customize)

The agent modifies these templates based on user requirements, ensuring consistency while allowing customization.

**Template vs. Asset distinction:**
- **Template**: [scaffold.py](../../tool-design/references/architectural_reduction.md) - Agent inserts algorithm logic (MODIFIES)
- **Asset**: logo.png - Agent embeds unchanged in document output (CONSUMES AS-IS)

### Should I Create Assets?

**Create assets/ when:**
- ✅ Static files are referenced in SKILL.md or scripts
- ✅ Files are used as-is in user output (images, configs, styles)
- ✅ The asset defines visual/brand standards

**Example**: A skill that generates reports might include:
- report-template.html (Asset: embedded in output unchanged)
- logo.png (Asset: referenced in generated HTML)

**Don't create assets when:**
- ❌ The file is code the agent modifies (use templates/ instead)
- ❌ The asset is enormous (>10MB) and rarely used
- ❌ External URL access is simpler than bundling

## Organization Best Practices

### File Naming

Use clear, descriptive names with hyphens (not underscores):

```
✅ GOOD                          ❌ POOR
references/
  api-reference.md                 api_reference.md
  testing-patterns.md              testing_patterns.md
  implementation-guide.md          ImplementationGuide.md

scripts/
  dataset-validator.py             validateDataset.py
  build-helper.sh                  build_helper.sh
```

### Folder Structure

Keep organization flat for small skills, hierarchical for large ones:

**Small skill (< 5 resources):**
```
my-skill/
├── SKILL.md
├── scripts/
│   └── helper.py
└── references/
    └── getting-started.md
```

**Large skill (> 10 resources):**
```
my-skill/
├── SKILL.md
├── scripts/
│   ├── validation/
│   │   └── schema-validator.py
│   └── automation/
│       └── deploy-helper.sh
└── references/
    ├── concepts/
    │   ├── architecture.md
    │   └── design-patterns.md
    └── workflows/
        ├── setup-guide.md
        └── deployment-guide.md
```

### Linking from SKILL.md

Use relative paths consistently:

```markdown
# Workflows

See [getting started guide](./references/getting-started.md) for step-by-step setup.

Run the [helper script](./scripts/helper.py) to automate validation.

Use this [scaffold](./templates/scaffold.py) as a starting point.
```

## Content Duplication Prevention

**Problem**: Same content in SKILL.md and references/ wastes context.

**Solution**: 

1. **SKILL.md**: Write the workflow narrative, link to references for details
   ```markdown
   ## Step 3: Configure Environment
   See [environment setup guide](./references/setup-guide.md#environment) for detailed instructions.
   ```

2. **references/setup-guide.md**: Write the deep, detailed documentation
   ```markdown
   ## Environment Setup
   Detailed steps for each platform...
   ```

3. **Never duplicate**: Reference from SKILL.md; write details in references/

## Size Guidelines

| Resource Type | Recommended Size | Exceeds Limit When | Action |
|---|---|---|---|
| SKILL.md | 400-500 lines | > 600 lines | Move details to references/ |
| Single reference file | 200-800 lines | > 1000 lines | Split into multiple files |
| Script | 100-500 lines | > 700 lines | Split into helper modules |
| Template | 50-200 lines | > 300 lines | Provide scaffold + detailed example in references/ |

## Quality Checklist

Before bundling resources:

- [ ] **Scripts**: Include `--help`, error handling, cross-platform compatibility
- [ ] **References**: Each file has clear purpose stated in opening; sub-sections use ## headers for navigation
- [ ] **Templates**: Include inline comments explaining placeholders; example showing customization
- [ ] **Assets**: Used explicitly in SKILL.md or scripts; not abandoned/unused
- [ ] **Links**: All relative paths verified; no broken references
- [ ] **No duplication**: Content appears in only one place
- [ ] **Load strategy respected**: SKILL.md links appropriately, doesn't embed all content inline

## Related Guidance

- [Agent Skills File Guidelines - Bundling Resources](../../../instructions/agent-skills.instructions.md#bundling-resources)
- [Skill Design Principles](./skill-design-principles.md#progressive-disclosure)
- [Agent Skills Instructions](../../../instructions/agent-skills.instructions.md)

