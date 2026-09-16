# AGENTS.md

## Project description

Hypothiq is focused on developing, testing, and experimenting with trading strategies using Backtrader.

The project will evolve gradually:

1. YAML configuration, single-backtest execution, human-readable results, and basic single-asset indicator strategies.
2. Strategy optimization.
3. Multi-asset strategies.
4. Portfolio optimization strategies.
5. ML strategies, including pattern recognition.
6. AI-assisted strategy generation from text descriptions.

The roadmap describes future direction, not requirements for the current feature. Do not build infrastructure for future stages unless the current task requires it.

## Development workflow

When implementing a feature:

1. Develop each feature in a separate branch.

2. Before implementing, inspect the relevant existing code and understand the current contracts and architecture.

3. If essential information is missing and it materially affects the public contract, architecture, or observable behavior, ask for clarification before implementing.

   Do not ask about implementation details that can be reasonably inferred from the existing codebase, established conventions, or the task itself.

4. Keep the change focused on the requested feature. Do not perform unrelated refactors, renames, formatting sweeps, or cleanup unless they are required by the feature.

5. For cross-cutting changes affecting multiple components or responsibilities, work incrementally in coherent batches and explain what changed and why.

6. Verify that the clean-code requirements below still hold.

7. Add tests for the new behavior, including meaningful edge cases.

8. When the feature is complete, create a PR with a meaningful title and description.

9. DO NOT merge PRs on your own.

10. DO NOT commit or push directly to `main`.

## Testing

* Correctness is more important than maximizing coverage.
* Test observable behavior rather than implementation details.
* Include meaningful edge cases where incorrect behavior is plausible.
* Mock external systems, expensive dependencies, nondeterministic behavior, or collaborators outside the unit under test.
* Do not mock simple value objects or stable internal collaborators unnecessarily.
* Prefer small real inputs when they make tests clearer than mocks.
* A bug fix should normally include a regression test when practical.

## Design and clean-code requirements

### General

* Code must be well-formatted, readable, and easy to follow.
* Prefer clear and direct code over clever implementations unless the simpler implementation would be materially inefficient.
* If a less-readable implementation is necessary for performance or technical reasons, document why.

### Responsibilities and abstractions

* Modules, classes, and functions should have clear and cohesive responsibilities.
* Do not split code merely to make functions, classes, or files smaller.
* Introduce an abstraction only when it represents a meaningful concept, removes real duplication, or materially improves readability.
* Before introducing a new abstraction, inspect the existing architecture and reuse established concepts where they still fit.
* Do not create parallel abstractions for concepts already represented in the project.

### YAGNI

* Implement only what the current feature requires.
* Do not introduce factories, registries, extension points, compatibility layers, configuration options, or generic infrastructure only because they may be useful in the future.
* Prefer the simplest design that cleanly satisfies the current known requirements.

### Validation and input contracts

* Validate data at system boundaries.
* Inside trusted internal code, rely on established contracts instead of repeatedly validating the same values.
* Prefer narrow and explicit input contracts over accepting multiple equivalent representations.
* If an external file or configuration does not follow the required format, raise a meaningful exception instead of guessing, silently correcting, or normalizing it.
* Do not add defensive compatibility behavior unless explicitly required.

### Helper functions

Prefer direct code over unnecessary private helper functions.

Do not extract `_validate_*`, `_normalize_*`, `_resolve_*`, `_ensure_*`, `_convert_*`, or similar helpers unless at least one of the following applies:

* the logic is reused;
* it represents a meaningful domain concept;
* it isolates genuinely complex logic;
* or extraction materially improves the readability of the caller.

Before creating a helper, ask whether keeping the logic inline would make the code easier to understand.

### Documentation

* Add docstrings to public or non-obvious components when they clarify purpose, assumptions, contracts, or behavior.
* Do not add docstrings or comments that merely restate the code, function name, or signature.
* Comments should explain why something is done, not narrate what obvious code does.

### Dependencies

* Prefer the standard library and existing project dependencies when they solve the problem adequately.
* Do not add a new dependency for functionality that can be implemented clearly and reasonably with existing tools.
* If introducing a new dependency, explain why it is justified.
