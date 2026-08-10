from .file_utils import load_json
from pathlib import Path


class Vocabulary:
    def __init__(self, vocab_path: Path):
        data = load_json(vocab_path)

        self.token_list = [""] * (max(data.values()) + 1)
        for token, token_id in data.items():
            self.token_list[token_id] = token

    def id_to_text(self, token_id: int) -> str:
        return self.token_list[token_id].replace("\u0120", " ")

    @property
    def size(self) -> int:
        return len(self.token_list)
