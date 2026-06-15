# CLAUDE.md

## Purpose

A personal "second brain" / digital notebook — an Obsidian vault containing notes on hobbies, food, keyboards, photography, projects, and travel. Published as a static site at `blog.j6n.ca`.

## Tech stack

- **Authoring**: Obsidian (vault rooted at `docs/`)
- **Publishing**: [Basalt](https://basalt.j6n.dev) static site generator, run via GitHub Actions (`.github/workflows/deploy_basalt.yml`) on push to `main`

## Structure

- `docs/` — the Obsidian vault and all content
  - `notes/`, `hobbies/`, `food/`, `keyboards/`, `photography/`, `projects/`, `travel/` — published content sections
  - `templates/`, `assets/`, `diagrams/`, `drafts/`, `wip/`, `ignore/`, `.obsidian/` — excluded from publish (see workflow `ignored_dirs` and `.gitignore`)
  - `index.md` — site landing page
  - `tags.md` — tag index
- `.github/workflows/deploy_basalt.yml` — deploy pipeline (calls `gravityctl/basalt` reusable workflow)
- `CNAME` — custom domain config for GitHub Pages

## Conventions

- Notes use YAML frontmatter with `tags`, `date`, `title`
- Internal links use Obsidian wiki-link syntax: `[[path|label]]`
- `docs/wip/` and `docs/ignore/` are gitignored — use them for in-progress or private content
- The Basalt workflow excludes: `templates, scripts, .obsidian, assets, diagrams, drafts` from the rendered site
- Python pinned to 3.10.1 via `.tool-versions` (legacy from the old mkdocs setup)
