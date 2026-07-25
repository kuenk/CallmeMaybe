import re


def enum_continue(generate, candidate, options):
    extend = generate + candidate
    for option in options:
        if option.startswith(extend):
            return True
    return False

def enum_complete(generate, options):
    return generate in options


def number_continue(generate, candidate):
    extend = generate + candidate
    if "-" in extend:
        if extend.count("-") > 1:
            return False
        if extend.index("-") != 0:
            return False
    if extend.count(".") > 1:
        return False
    return True


def number_complete(generate):
    patron = re.compile(r"^-?\d+(\.\d+)?$")
    return bool(patron.fullmatch(generate))


def string_continue(candidate: str) -> bool:
    if candidate == '"':
        return  True
    if any(character in candidate for character in ['"', "\n", "\t", "\r"]):
        return False    
    return True

def string_complete(generate):
    if generate.endswith('"'):
        return True
    return False