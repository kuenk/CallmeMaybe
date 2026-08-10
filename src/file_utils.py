import json
from pathlib import Path
from typing import Any


def load_json(file_path: Path) -> Any:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_and_validate(file_path: Path, model_class: Any) -> list[Any]:
    raw_data = load_json(file_path)
    return [model_class(**element) for element in raw_data]
