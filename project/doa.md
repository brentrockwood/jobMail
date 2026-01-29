# Development Operating Agreement

This document describes our working agreement on all projects. It is authoritative and must only be edited by humans.

## Do this every session

- If starting a new project
    - Create a `README.md` if it hasn't been created already. If you have any context as to the purpose and goals of the project, you may add them now. If not, a simple title derived from the folder name will do for now. As we progress through the project, you are free to update this file autonomously, always reporting any changes. Always include a setup section which includes such things as shell scripts to be run, environment variables to be set, dependencies required, and anything else necessary to get the user up and running with a minimum of manual intervention. `README.md` is end-user facing and should not influence operational choices. It is simply a deliverable that must be kept up to date like any other.
    - Create a `project.md` in the `project` folder. This is where project level plans and checklists go, as well as the overall architecture, stack decisions, etc. It is our primary operational document. At this point, its contents will likely mirror the `README.md`.  Further updates to `project.md` **require** human authorization and it should otherwise be considered **write-locked**.
    - Create a `context.md` in a new `project` folder. The format of your first entry is defined below. The body can be as simple as 'Started [projectname] project. This is our ongoing work log. Entries *must* never be edited after they have been entered. Consider it an auditable artifact.

- If resuming an existing project
    - Read `project/project.md`. This will only be updated after discussion and is considered *write-locked* unless given explicit human authorization. This is our primary operational document.
    - Read `project/context.md`. You do not need to read the whole thing. Just the last entry or two, enough to know where we left off in the previous session. Cap at 12K of text at the most. If you do not have enough context from that, ask for help. If no context exists because we are using these standards for the first time on an existing project, create the file if necessary, review the existing codebase, and add an entry that summarizes the current state as well as you can. This is our ongoing work log. Entries *must* never be edited after they have been entered. Consider it an auditable artifact.

## Phases of a feature

- Planning
    - Ask questions
    - Suggest options
    - This is your time to voice your opinions
    - Decisions, plans, and task checklists should go in `project.md`.
    - Tool, dependency, and stack decisions will be decided here and **must** be followed until discussion opens up again in the next phase.
    - You *should* press me for a decision if I have forgotten something or something is ambiguous. After all, you will be required to live by our choices until the next planning phase. This includes, but is not limited to:
        - Stack and language (i.e. Python/Flask, Node/Express/NextJS, etc.)
        - Explicit coding standards and linters (i.e. PEP, Google Go style guide, ESLint)
        - Testing framework (i.e. go built-in, Jest)
    - At some point I will decide that planning is complete for this step. We will come back to it later many times. At no time should you autonomously update `project.md`. Updates to `project.md` **require** human authorization and should otherwise be considered **write-locked**.
    - It is inevitable that, occassionally, we may get part way through the later steps and decide that we should revisit a decision made here. You may, if absolutely necessary, suggest it. However, **only a human can authorize changes to the plan**.
    - When a decision is superceded or retired, the original decision should remain in place in `project.md` but be marked as superceded with a reference to the replacement decision.
    - In the rare but eventually inevitable event that external factors force re-planning (i.e. dependency deprecation, high severity CVE), we both have the responsibility to call it out as soon as we become aware of it so that we can make a decision on our next steps. 

- Branching
    - All new work after a push to origin must begin on a fresh branch. If the new work refers to an itemized step in `project.md`, refer to that step in the branch name.
    - For now, we will attempt to work one feature at a time, obviating the need for rebasing or anything like that. If that changes, we will deal with it on a per-project implementation detail. If it becomes the norm, we may wish to codify our approach in this document.
 
- Coding style
    - Code in a way that is idiomatic for the stack/language/framework. Follow the style guides that were chosen in the planning stage. In particular, style precedence is as follows:

        - Existing project conventions
        - Chosen style guides
        - Community best practices

        If you are unsure, ask.

    - Suggest refactors where appropriate. For example, if a file gets too long or covers too many concerns.
    - Wherever appropriate, use pure functions. They are easier to test.

- Error handling
    - Prefer explicit, typed errors over silent failure. Avoid catching errors unless there is a clear recovery path. Log with enough context to reconstruct failure after the fact.

- Dependencies
    - If a new dependency becomes necessary that has not previously been **human-approved**, follow these rules:
        - New dependencies must be justified in commit messages
        - Prefer standard library over third-party
        - Avoid adding dependencies solely for syntactic convenience
        - For the most part, pinning to a major semver version will be appropriate. Where it isn't, it will be dealt with on a case-by-case basis.

- Testing
    - Use the testing framework decided upon during the planning phase.
    - All tests must pass before each commit.
    - After each interaction which requires changes to code, consider whether there are appropriate tests that could be added or need to be changed. If so, do so and report those test changes.
    - There are no hard rules on coverage. We should, however, always keep testability top of mind as we build. Things like pure functions and dependency injection, even at the system level, are our friends.

- Linting
    - Use any tool(s) which we decided upon during the planning phase. Any errors or warnings must not be ignored. Strive to maintain a clean codebase at all times.

- Performance
    - Optimize for clarity first. Address performance only when there is evidence (measurements, scale assumptions, or explicit requirements) that it matters.

The coding, testing, and linting phases may be commingled as you see fit. In some cases you may wish to, for example, adopt a test-first pattern. You are free to make this decision autonomously. Where appropriate, you are encouraged to develop script(s) for human use so that I may operate without you. Where appropriate these scripts should be surfaced in documentation and places like `package.json` or a `Makefile`.

- Rollbacks
    - It is inevitable that these will happen once in a while. In most cases we will catch them quickly and a simple `git revert` will handle the issue. More complex scenarios will be dealt with on a case-by-case basis and we should reflect upon them together to determine if the error could have been avoided.

- Documentation
    - We should strive to keep user-facing documentation like `README.md`, API docs, etc. continuously up to date with the truth in the code. They are everyone's responsibility. As mentioned before, these are artifacts just like code and do not influence our operational choices.

## After **every** interaction

- Security scan
    - If an interaction resulted in any change to any file, not just code, scan the file(s) for any private information. This could include, but is not limited to, API keys, passwords, usernames, IP addresses, hostnames, SSH keys. Basically anything that is specific to the environment. You may replace these with placeholders and keep the originals in a file called `secrets.env`. This file, if it exists, **must** be in `.gitignore`. If appropriate, include a `secrets.env.example` file and reference this in the `README.md` under a setup section. Consider all projects to be subject to open-sourcing at any time and act accordingly. Report the substitution to me.

        Once again, you are encouraged to develop script(s) for the security scan. Clear exit codes are encouraged (i.e. 0 - Pass, 1 - Fail) and failures should report the issue. 

    - **Always** append your progress to `project/context.md`. This is your message to future you and secondarily to me if I pick up the project six months from now. Think of what you would want to know if the session crashed and you had to resume, which happens more often than you think. We will both thank you in the future. Wherever appropriate, reference the plans and steps defined in `project.md`. The format of an entry is as follows:

```

---
Date: [ISO 8601 local date and time with offset]
Hash: [Base64 encoded SHA-256 hash of body text]
Agent: [Agent name and version]
Model: [Model name and version]
StartCommit: [Git hash of the most recent commit when starting this interaction]
---

[body text]

EOF

```

    - In addition to recording your progress in `context.md`, always report your progress to me, complete with diffs of any files changed in the current interaction so that I may follow along. The only exception to this is for very large diffs or generated but not committed files. For very large diffs, summarize changes and include representative excerpts and/or summaries unless full diffs are explicitly requested. For now, the definition of "very large" is left up to the discretion of the model/agent.

## Committing

    - You are free to commit at any time and are encouraged to do it after every interaction, but **never** push without authorization. I will say that again. **Only humans can authorize pushes.** Commit messages are at your discretion but should be human readable and descriptive of the change.
    - What does not belong in commits:
        - Generated files
        - Lockfiles
        - Editor ephemera (.vscode, .un~, etc.)
        - Build artifacts
        - Binaries or vendored code (but make a note of them in the `README.md`).

## Feature build/test cycle complete

- You will have been reporting your progress after each interaction. When I declare the feature is complete, then and only then, can we move on to the next step which is...

## `Send 'er`

- The phrase `send 'er` is a command which has been chosen because it is unlikely to come up in normal discussion. It is a specific command comprised of the following steps:

1. Run a security scan on the entire project. If any substitutions were required, report to me.
2. If any file changes have occurred since the last test run, run all tests. All tests must pass. If not, report to me.
3. If any code changes have occurred since the last linter run, run the linter. It must not report any errors or warnings. If it does, report to me.
4. If a build is required, run it. If any errors or warnings are reported, report them to me, along with any insight or suggestions to fix them.
5. Commit if necessary and push to origin.
6. Open a pull request for the change.

## Overarching goals

If you haven't figured out yet, these rules are designed to help us work together most efficiently, with the fewest surprises, and the smallest blast radius when things inevitably go wrong. Just remember, if you think you know something I don't, tell me. If you think I know something you don't, ask.

