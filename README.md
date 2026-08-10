*This project has been created as part of the 42 curriculum by dcuenca.*

# call-me-maybe

## Description

`call-me-maybe` translates natural-language prompts into structured function
calls (`{"name": ..., "parameters": {...}}`) using a small 0.6B-parameter
language model (`Qwen/Qwen3-0.6B`). Instead of relying on the model to
"spontaneously" produce well-formed JSON — which small models are notoriously
bad at — the project guarantees 100% valid, schema-compliant output through
**constrained decoding**: at every point where the model has to choose a
value (which function to call, or what a parameter's value should be), the
program masks out every token that would break the JSON grammar or the
expected type, so the model is structurally incapable of producing invalid
output.

Given `"What is the sum of 2 and 3?"`, the program does not answer `5` — it
returns:

```json
{"prompt": "What is the sum of 2 and 3?", "name": "fn_add_numbers", "parameters": {"a": 2.0, "b": 3.0}}
```

## Instructions

Dependencies are managed with `uv`. From the project root:

```bash
uv sync
```

To copy the LLM SDK: place the provided `llm_sdk` package as a subdirectory
next to `src/` and register it as a local dependency:

```bash
uv add ./llm_sdk
```

Run the program (reads from `data/input/`, writes to `data/output/` by
default):

```bash
uv run python -m src
```

With custom paths:

```bash
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

Lint and type-check:

```bash
uv run flake8 .
uv run mypy . --warn-return-any --warn-unused-ignores \
  --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
```

Run the (non-graded) test suite:

```bash
uv run pytest
```

## Algorithm explanation

The core idea is that the overall JSON structure for a function call is
fully known ahead of time once `functions_definition.json` is loaded — the
keys, their order, and the punctuation between them never depend on the
model. That scaffolding (`{`, `"name":`, commas, closing braces...) is
written as literal text by the program itself. The model is only ever
consulted to fill in the actual *values*: which function to call, and each
parameter's value, one at a time, in schema order.

For each value slot, the generation loop (`generate_constrained` in
`generator.py`) works as follows:

1. Ask the LLM for logits over the full vocabulary given the current
   context (prompt + JSON scaffolding generated so far).
2. For every token id in the loaded vocabulary, translate it to text
   (`Vocabulary.id_to_text`) and ask the relevant grammar function whether
   appending that text would still be a valid continuation.
3. Set the logits of every invalid token to `-inf`; keep the real logits
   only for valid candidates.
4. Pick the token with the highest remaining logit (masked argmax).
5. Repeat until the grammar's own completion check says the value is done,
   or a safety limit on token count is reached.

Because invalid tokens are structurally excluded at every step, there is no
path through the mask that can produce a syntax or type error — the output
is guaranteed to be valid JSON, by construction, not by hoping the model
gets it right.

Three grammars are implemented (`grammar.py`), one per JSON value type
needed by the spec:

- **Enum** (used for choosing the function name, and for `boolean` values
  via the two-option list `["true", "false"]`): a candidate is valid while
  the accumulated text remains a prefix of at least one option; it is
  complete once it exactly matches one.
- **Number**: candidates are validated against a partial-number regular
  expression (`^-?\d*\.?\d*$`). Completion is more subtle — see "Challenges
  faced" below.
- **String**: any candidate is accepted unless it contains an unescaped
  quote or a raw control character (newline, tab...); a lone `"` token is
  the signal that generation is complete.

Prompts are formatted using Qwen3's ChatML template
(`<|im_start|>system/user/assistant ... <|im_end|>`), with an explicit empty
`<think>\n\n</think>\n\n` block to disable the model's "thinking" mode —
without it, the model would emit a free-form reasoning block before any
usable output, which is incompatible with constrained decoding at the first
token.

## Design decisions

- **Literal scaffolding instead of full-sequence constrained decoding.**
  Rather than building a general-purpose JSON/grammar parser capable of
  constraining an entire document, the program only asks the model to fill
  in atomic values, and writes every structural character itself. This
  keeps the grammars small, testable in isolation (pure functions, no LLM
  needed), and avoids reimplementing a full JSON parser.
- **A dedicated `GenerationError` exception.** Failures that are an
  *expected* possible outcome of the generation process (no valid token
  found, a value that never terminated within the token budget) are raised
  as `GenerationError`, distinct from unexpected bugs. The CLI catches the
  two separately, so a model failing to produce a plausible regex for one
  test prompt does not crash the whole batch, while a genuine programming
  error is still reported distinctly.
- **No private `llm_sdk` access.** Per the spec, only the public methods of
  `Small_LLM_Model` are used. The tokenizer's vocabulary file is loaded and
  inverted manually (`Vocabulary`) instead of relying on the SDK's
  `decode`, keeping the door open for the "reimplement the tokenizer" bonus.
- **`load_and_validate(file_path, model_class)`** is a single generic
  loader used for both `functions_definition.json` and
  `function_calling_tests.json`, parameterized by the Pydantic model to
  validate against, instead of duplicating file-reading logic per file.

## Performance analysis

Function *selection* was correct in all 11 provided test prompts (100%).
Full end-to-end success — correct function **and** all parameters generated
without error — was achieved in 8 of 11 prompts; the 3 failures were all
prompts requiring the model to synthesize a regular expression
(`fn_substitute_string_with_regex`), a task well beyond what a 0.6B
parameter model can reliably produce, ChatML formatting notwithstanding.
This matches the spec's own framing: constrained decoding guarantees
*syntactic* validity, not *semantic* correctness — a small model can still
choose to generate nonsensical (but grammatically valid) content, or, for
`string` values, run out of its token budget before naturally terminating.

The dominant cost per generated token is the masking loop, which evaluates
every one of the ~151k vocabulary entries against the grammar on every
step — an O(vocabulary size) Python loop per token, executed once per
generated token. This is the main lever for the "performance optimizations"
bonus (e.g., caching grammar decisions, narrowing the candidate set before
the full scan).

## Challenges faced

- **Vocabulary size vs. logits size mismatch.** The model produces logits
  over 151,936 possible tokens, but the loaded vocabulary file only maps
  151,643 of them to text — the remainder are special/control tokens with
  no textual representation. Any code that scans "all logits" (rather than
  "all *known* vocabulary entries") has to explicitly bound itself to the
  vocabulary's size, or it will eventually try to translate an id that
  doesn't exist and crash.
- **A parameter-order bug in `string_continue`.** The function's arguments
  were declared as `(candidate, generate)` instead of the `(generate,
  candidate)` order every other grammar function (and the generation loop
  itself) uses. Because the unused parameter was intentionally prefixed
  with `_` (a legitimate pattern used elsewhere for unused-but-required
  arguments), the bug silently swallowed the real candidate and validated
  the *wrong* string instead — passing the LLM's actual candidate as an
  ignored value. It only surfaced when a single token combining a closing
  quote with two closing braces (`"}}`) slipped through as "valid", derailing
  generation. Caught by instrumenting the generation loop to print each
  chosen token and comparing against the expected stopping behavior.
- **Number generation stopping too early.** A regex-only "is this string a
  complete number" check is ambiguous: `"4"` is a syntactically valid
  number on its own, so the naive check stopped generation after a single
  digit even when the model, given free rein, would have continued to
  `"40"`. This was resolved by also computing, at each step, the token the
  model would prefer with *no* grammar restriction applied, and only
  declaring a number complete when that free preference is no longer a
  valid number continuation — letting the model itself signal "I'm done"
  rather than guessing from the text alone.
- **Silent instruction-following failure without a chat template.** With a
  plain-text prompt, the model consistently picked the same function
  regardless of the user's request — reordering the function list ruled out
  a positional bias, isolating the cause to prompt format rather than logic.
  Formatting the prompt with Qwen3's ChatML template (and disabling
  "thinking" mode) fixed function selection immediately and reproducibly in
  both directions.

## Testing strategy

Pure grammar logic (`grammar.py`) is covered by `pytest` unit tests that
require no LLM (`tests/`), since `is_valid`/`is_complete` functions are
deterministic given their string inputs. Everything that involves the LLM
itself (vocabulary loading against the real `vocab.json`, end-to-end
generation for each grammar type, the full `process_prompt` pipeline) was
validated interactively against the real `Qwen/Qwen3-0.6B` model, comparing
actual output to expected results for both straightforward cases (a single
number, a single string, a two-parameter numeric function) and edge cases
(multi-digit numbers, functions chosen from reordered lists to rule out
positional bias).

## Example usage

```bash
uv run python -m src
```

```
Wrote 8 results to data/output/function_calling_results.json
```

Sample entries from `function_calling_results.json`:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?",
    "name": "fn_add_numbers",
    "parameters": {"a": 2.0, "b": 3.0}
  },
  {
    "prompt": "Greet shrek",
    "name": "fn_greet",
    "parameters": {"name": "shrek"}
  }
]
```

## Resources

- Sennrich, Haddow, Birch — *Neural Machine Translation of Rare Words with
  Subword Units* (introduces Byte-Pair Encoding, the tokenization scheme
  underlying Qwen's vocabulary format).
- Qwen team — Qwen3 model documentation and ChatML prompt format reference.
- Hugging Face `transformers` documentation on `AutoTokenizer` and chat
  templates.

**AI usage**: An AI assistant (Claude) was used exclusively in a coaching
role — explaining concepts (constrained decoding, tokenization, Python
mechanisms such as closures and slicing), reviewing code written by the
author, and helping design the debugging process for real bugs encountered
during development (see "Challenges faced"). All code in this repository
was written by the author; the assistant did not write or paste
implementation code into the project. Every design decision and bug fix
listed above was implemented and verified by the author against the real
model before being accepted.