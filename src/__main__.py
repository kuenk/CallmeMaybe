import json
from pathlib import Path
from pydantic import ValidationError
from .pipeline import process_prompt
from .models import FunctionDefinition, TestPrompt, GenerationError
from .file_utils import load_and_validate, save_json
import sys
import argparse
from llm_sdk import Small_LLM_Model
from .vocabulary import Vocabulary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--functions_definition",
        default="data/input/functions_definition.json",
    )
    parser.add_argument(
        "--input",
        default="data/input/function_calling_tests.json",
    )
    parser.add_argument(
        "--output",
        default="data/output/function_calling_results.json",
    )
    args = parser.parse_args()
    try:
        functions = load_and_validate(Path(args.functions_definition),
                                      FunctionDefinition)
    except ValidationError as e:
        print(f"Validation error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        sys.exit(1)

    try:
        test_prompts = load_and_validate(Path(args.input), TestPrompt)
    except ValidationError as e:
        print(f"Validation error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        sys.exit(1)

    llm = Small_LLM_Model()
    vocab_path = llm.get_path_to_vocab_file()
    vocab = Vocabulary(Path(vocab_path))
    results = []
    for test_prompt in test_prompts:
        try:
            result = process_prompt(llm, vocab, functions, test_prompt.prompt)
            results.append(result)
        except GenerationError as e:
            print(f"Could not process prompt '{test_prompt.prompt}': {e}")
        except Exception as e:
            print(f"Unexpected error for prompt '{test_prompt.prompt}': {e}")

    save_json(results, Path(args.output))
    print(f"Wrote {len(results)} results to {args.output}")
