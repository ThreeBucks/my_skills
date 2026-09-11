---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Execution method:** Preserve the method already selected or authorized for this task. Use superpowers:subagent-driven-development only when that method is selected or authorized and the tools are available. If inline execution was chosen, continue with this skill. Tool availability alone does not authorize changing the method or reopening that choice.

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. Resolve routine questions from the request, code, and evidence. Raise only material unresolved scope, correctness, or authorization concerns; pause dependent tasks only.
4. If no concerns: Create TodoWrite and proceed

### Step 2: Execute Tasks

For each task:
1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

### Step 3: Complete Development

After all tasks complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow that skill to verify tests and complete the authorized delivery choice; reuse an existing choice without asking again.

## When to Stop and Ask for Help

**Diagnose ordinary failures before escalating:**
- An expected failing test in TDD is part of execution. Diagnose command failures, missing dependencies, and regressions; repair issues within the approved scope and available permissions.
- Use existing evidence and project conventions to resolve routine implementation details. Do not infer permission for installations or other restricted actions.
- Pause dependent work when a necessary input, access permission, or material user decision is missing, or the next action exceeds the approved scope. Continue independent authorized tasks.
- Repeated failures require new evidence or a changed hypothesis, not identical retries. Preserve applicable debugging escalation rules and explicit baseline, merge, or publication gates.

**Explain the specific unresolved blocker and ask only for the input or approval needed to resolve it.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't bypass blockers** - investigate within scope, then pause only the work requiring unavailable input or approval.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **superpowers:using-git-worktrees** - Ensures isolated workspace (creates one or verifies existing)
- **superpowers:writing-plans** - Creates the plan this skill executes
- **superpowers:finishing-a-development-branch** - Complete development after all tasks
