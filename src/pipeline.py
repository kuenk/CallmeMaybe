from typing import Callable, Any
from .vocabulary import Vocabulary
from .generator import generate_constrained, to_id_list
from .models import FunctionDefinition, GenerationError
from .grammar import (
    enum_continue, enum_complete,
    number_complete, number_continue,
    string_complete, string_continue)


def build_prompt(functions: list[FunctionDefinition], user_prompt: str) -> str:
    line1 = ("You are a function calling engine. "
             "Given the user request and the available functions below, "
             "choose the correct function name.")
    line2 = "Available functions:"
    lines = [f"- {function.name}: {function.description}"
             for function in functions]
    line3 = "\n".join(lines)
    line4 = f"User request: {user_prompt}"
    prompt2 = (f"<|im_start|>system\n{line1}<|im_end|>\n"
               f"<|im_start|>user\n{line2}\n{line3}\n{line4}<|im_end|>\n"
               f"<|im_start|>assistant\n<think>\n\n</think>\n\n")
    return prompt2


def make_enum_grammar(options: list[str]) -> tuple[Callable[[str, str], bool],
                                                   Callable[[str, str], bool]]:
    def is_valid_fn(generate: str, candidate: str) -> Any:
        return enum_continue(generate, candidate, options)

    def is_complete_fn(generate: str, preferred_candidate: str) -> Any:
        return enum_complete(generate, options, preferred_candidate)
    return is_valid_fn, is_complete_fn


def process_prompt(llm: Any, vocab: Vocabulary,
                   functions: list[FunctionDefinition],
                   user_prompt: str) -> dict[str, Any]:
    prompt_text = build_prompt(functions, user_prompt)
    context_ids = to_id_list(llm.encode(prompt_text))
    options = [f.name for f in functions]
    is_valid_fn, is_complete_fn = make_enum_grammar(options)
    chosen_name = generate_constrained(
        llm, vocab, context_ids, is_valid_fn, is_complete_fn)
    choosen = None
    for x in functions:
        if x.name == chosen_name:
            choosen = x
            break
    if choosen is None:
        raise GenerationError(f"Chosen function name {chosen_name} "
                              f"not found in functions list")
    text = prompt_text + '{"name": "' + chosen_name + '", "parameters": {'
    parameters_dict = {}
    for index, (param_name, param_spec) in enumerate(
                choosen.parameters.items()):
        if index > 0:
            text = text + ', '
        text = text + f'"{param_name}": '
        if param_spec.type == "string":
            text = text + '"'
        param_context_ids = to_id_list(llm.encode(text))
        if param_spec.type == "number":
            value = generate_constrained(llm, vocab, param_context_ids,
                                         number_continue, number_complete)
            parameters_dict[param_name] = float(value)
        elif param_spec.type == "string":
            value = generate_constrained(llm, vocab, param_context_ids,
                                         string_continue, string_complete)
            if not value.endswith('"'):
                raise GenerationError(f"String generation for '{param_name}' "
                                      f"did not terminate properly "
                                      f"(hit max_tokens): {value!r}")
            parameters_dict[param_name] = value[:-1]
        elif param_spec.type == "boolean":
            bool_valid, bool_complete = make_enum_grammar(["true", "false"])
            value = generate_constrained(llm, vocab, param_context_ids,
                                         bool_valid, bool_complete)
            parameters_dict[param_name] = value == "true"
        else:
            raise GenerationError(f"Unknown parameter type: {param_spec.type}")
        text = text + value
    text = text + '}}'

    return ({"prompt": user_prompt, "name": chosen_name,
             "parameters": parameters_dict})
