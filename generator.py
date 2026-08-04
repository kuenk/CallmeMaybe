import torch

def generate_constrained(llm, vocab, context_ids, is_valid_fn, is_complete_fn, max_tokens=50):
    new_text = ""
    ids_copy = context_ids.copy()
    for _ in range(max_tokens):        
        original_logits = llm.get_logits_from_input_ids(ids_copy)
        preferred_id = original_logits[:vocab.size].index(max(original_logits[:vocab.size]))        
        preferred_candidate = vocab.id_to_text(preferred_id)
        if is_complete_fn(new_text, preferred_candidate):
            break
        logits_masked = [-float('inf')] * vocab.size
        for token_id in range(vocab.size):
            text_candidate = vocab.id_to_text(token_id)
            if is_valid_fn(new_text, text_candidate):
                logits_masked[token_id] = original_logits[token_id]   
        if max(logits_masked) == float('-inf'):
            raise RuntimeError("No valid token found for this grammar/context")     
        chosen_id = logits_masked.index(max(logits_masked))
        new_text += vocab.id_to_text(chosen_id)
        ids_copy.append(chosen_id)
        print(f"Token elegido: {vocab.id_to_text(chosen_id)!r} | new_text ahora: {new_text!r}", flush=True)

    return new_text


def to_id_list(encoded: torch.Tensor) -> list[int]:
    aux = encoded.tolist()
    return  aux[0]



