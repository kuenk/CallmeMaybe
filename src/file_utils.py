import json
from pydantic import ValidationError
from pathlib import Path
from .models import FunctionDefinition
from typing import Any

def load_json(file_path: Path) -> dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data: dict[str, Any]):
    new_path = Path(__file__).parent.parent / "data" / "output" / "valid_test.json"
    new_path.parent.mkdir(parents=True, exist_ok=True)
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def read_json():
    file_path= Path(__file__).parent.parent / "data" / "input" / "functions_definition.json"
    print (f"Reading JSON file from: {file_path}")
    try:
        
        valid_models = [ FunctionDefinition(**element) for element in load_json(file_path) ]
        save_json({"functions": [model.model_dump() for model in valid_models]})
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"File is not valid JSON: {file_path}")
        return None
    except ValidationError:
        print(f"JSON has incorrect format: {file_path}")
        return None
