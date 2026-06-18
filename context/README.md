# Context Directory

This directory provides structured context for AI-assisted development sessions. It helps Claude Code (or any AI assistant) quickly understand the project state, what's being worked on, and how the codebase is organized.

## Files

### `_active.md`
Tracks the **currently active feature or task**. Update this at the start of each work session so the AI knows what you're focused on. Contains:
- Feature name and description
- Path to a feature-specific context file (if one exists)
- Git branch name
- Session start date

### `_project.md`
**High-level project map** — the single file an AI should read first to understand the project. Contains:
- Project name and tech stack
- Key directories and what they contain
- Coding conventions and patterns
- Testing framework and how to run tests
- Environment/config notes
- Complete list of modules and features

### Feature context files (optional)
When working on a complex feature, create a dedicated context file here (e.g., `context/feature-telegram-v2.md`) with feature-specific design decisions, API details, or constraints. Reference it from `_active.md`.
