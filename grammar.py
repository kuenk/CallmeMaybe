import re

def enum_continue(generate, candidate, options):
    extend = generate + candidate
    for option in options:
        if option.startswith(extend):
            return True
    return False

def enum_complete(generate, options, _preferred_candidate):
    return generate in options

def number_continue(generate, candidate):
    extend = generate + candidate
    return bool(re.compile(r"^-?\d*\.?\d*$").fullmatch(extend))

def number_complete(generate, preferred_candidate):
    patron = re.compile(r"^-?\d+(\.\d+)?$")
    if not patron.fullmatch(generate):
        return False
    return not number_continue(generate, preferred_candidate)

def string_continue(_generate: str, candidate: str) -> bool:
    if candidate == '"':
        return  True
    if any(character in candidate for character in ['"', "\n", "\t", "\r"]):
        return False    
    return True

def string_complete(generate, _preferred_candidate):
    if generate.endswith('"'):
        return True
    return False




