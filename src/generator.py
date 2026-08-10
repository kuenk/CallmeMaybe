from typing import Any, Callable
import torch
from .models import GenerationError
from .vocabulary import Vocabulary


def generate_constrained(llm: Any, vocab: Vocabulary,
                         context_ids: list[int],
                         is_valid_fn: Callable[[str, str], bool],
                         is_complete_fn: Callable[[str, str], bool],
                         max_tokens: int = 50) -> str:
    new_text = ""
    ids_copy = context_ids.copy()
    for _ in range(max_tokens):
        original_logits = llm.get_logits_from_input_ids(ids_copy)
        limited_logits = original_logits[:vocab.size]
        preferred_id = limited_logits.index(max(limited_logits))
        preferred_candidate = vocab.id_to_text(preferred_id)
        if is_complete_fn(new_text, preferred_candidate):
            break
        logits_masked = [-float('inf')] * vocab.size
        for token_id in range(vocab.size):
            text_candidate = vocab.id_to_text(token_id)
            if is_valid_fn(new_text, text_candidate):
                logits_masked[token_id] = original_logits[token_id]
        if max(logits_masked) == float('-inf'):
            raise GenerationError("No valid token found for "
                                  "this grammar/context")
        chosen_id = logits_masked.index(max(logits_masked))
        new_text += vocab.id_to_text(chosen_id)
        ids_copy.append(chosen_id)
    return new_text


def to_id_list(encoded: torch.Tensor) -> list[int]:
    aux = encoded.tolist()
    return [int(x) for x in aux[0]]
