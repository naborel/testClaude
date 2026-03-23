# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This is a minimal test/demo repository for exploring Claude Code with VSCode. It has no build system or application code yet.

## Repository Structure

```
testClaude/
├── .claude/
│   └── settings.local.json  # Claude Code permissions (allows git config only)
└── README.md
```

## Claude Code Permissions

The `.claude/settings.local.json` restricts allowed Bash commands to `git config:*`. If you need to run other commands, the user will be prompted to approve them.

## Git

- Main branch: `main`
- Feature work happens on: `feat`
- Remote: https://github.com/naborel/testClaude
