from vocabulary import Vocabulary
from pathlib import Path


from .file_utils import read_json
import sys

if __name__ == "__main__":
    v = Vocabulary(Path(__file__).parent / "vocab_test.json")
    print(v.id_to_text(0))
    resultado = read_json()
    if resultado is None:
        sys.exit(1)
        