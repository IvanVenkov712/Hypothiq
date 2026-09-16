# AGENTS.md

## Project description
The project is focused on developing and experimenting with strategies. 
The features will be added gradually:
   1. Reading YAML configuration, running a single backtest and returning results in human-readable form.
   Indicator single-asset strategies
   2. Strategy optimization
   3. Multi-asset strategies
   4. Portfolio optimization strategies
   5. ML strategies, including pattern recognition
   6. Adding AI text description to strategy

## Desired workflow
When implementing a feature, do the following:
1. Develop each feature in a separate branch.
2. If you lack essential working or contract information (
for example types, meaning and names of a function arguments, class or module behavior and/or responsibilities),
DO NOT start mindlessly implementing the feature even if asked explicitly "Implement this" or "Implement that".
Instead, ask what's missing until you have enough information for an unambiguous implementation.
3. If a change is about to affect a lot of files, do it on batches and explain what have been changed and why.
4. Verify that the clean code requirements hold
5. Add tests for the component. Including edge cases
6. When done, create a PR with a meaningful title and description
7. DO NOT merge on your own.
8. DO NOT commit or push on main on your own.

## Testing
- Coverage is not as important as to ensure the correctness of the components.
- If testing a component using some dependencies, use mocks for them.

## Clean code requirements
- The code must be well-formated and human-readable.
- When wondering whether to write something readable or "clever and optimal" prefer the readable way
unless if not too suboptimal.
If a non-readable and/or "ugly" implementation is needed, explain and document why is it needed this way.
- Add docstrings explaining the purpose of the component and briefly how it works.
- Avoid creating big modules, classes and functions. each element (module, class or a function/method)
must have a clear responsibility
- If some file doesn't comply with the desired formatting (for example incorrect CSV or YAML), 
throw a meaningful exception and terminate the execution. Don't try to resolve it
- Don't flood the code with unnecessary and non-essential conversions and validations.
- Prefer direct code over private helper functions. 
Do not extract _validate_*, _normalize_*, _resolve_*, _ensure_* helpers unless:
  - the logic is reused, 
  - it represents a meaningful domain concept, 
  - or extraction materially simplifies the caller.
- Validate data at system boundaries, not repeatedly inside trusted internal code. 
- Prefer narrow, explicit input contracts over accepting multiple equivalent representations. 
- Do not add defensive compatibility layers unless explicitly requested. 
- Before creating a helper, ask whether the caller would be clearer with the logic inline.