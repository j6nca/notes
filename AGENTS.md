# CLAUDE.md

## Purpose

A personal "second brain" / digital notebook — an Obsidian vault containing notes on hobbies, food, keyboards, photography, projects, and travel. Published as a static site at `blog.j6n.ca`.

## Tech stack

- **Authoring**: Obsidian (vault rooted at `docs/`)
- **Publishing**: [Nebula](https://github.com/ctrl-research/nebula-md) static site generator, run via GitHub Actions (`.github/workflows/deploy_nebula.yml`) on push to `main`

## Structure

- `docs/` — the Obsidian vault and all content
  - `notes/`, `hobbies/`, `food/`, `keyboards/`, `photography/`, `projects/`, `travel/` — published content sections
  - `templates/`, `assets/`, `diagrams/`, `drafts/`, `wip/`, `ignore/`, `.obsidian/` — excluded from publish (see workflow `ignored_dirs` and `.gitignore`)
  - `index.md` — site landing page
  - `tags.md` — tag index
- `.github/workflows/deploy_nebula.yml` — deploy pipeline (calls `ctrl-research/nebula-md` reusable workflow)
- `scripts/` — repo tooling, not part of the vault (e.g. `geocode_reviews.py`)
- `CNAME` — custom domain config for GitHub Pages

## Conventions

- Notes use YAML frontmatter with `tags`, `date`, `title`
- Notes written primarily by AI must include a `genai` tag in frontmatter. This does not apply when AI only edits, enhances, formats, or tidies up existing human-written notes (e.g. filling in addresses, fixing formatting)
- Food reviews store coordinates as `location: [lat, lng]` frontmatter. After adding or changing a review's 📌 address, run `python3 scripts/geocode_reviews.py` to fill it in (it skips reviews that already have a `location`; delete the line to re-geocode)
- Permanently closed restaurants get a `> [!failure] Permanently closed` callout (with the closing date if known) above the `[!info]` block in their review
- Internal links use Obsidian wiki-link syntax: `[[path|label]]`
- `docs/wip/` and `docs/ignore/` are gitignored — use them for in-progress or private content
- The Nebula workflow excludes: `templates, scripts, .obsidian, assets, diagrams, drafts` from the rendered site
- Python pinned to 3.10.1 via `.tool-versions` (legacy from the old mkdocs setup)
