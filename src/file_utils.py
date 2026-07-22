import json
from pydantic import ValidationError
from pathlib import Path
from models import FunctionDefinition
from typing import Any


def save_json(data: dict[str, Any]):
    new_path = Path(__file__).parent / "data" / "output" / "valid_test.json"
    new_path.parent.mkdir(parents=True, exist_ok=True)
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def read_json():
    file_path= Path(__file__).parent / "data" / "input" / "function_calling_tests.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            valid_model = FunctionDefinition(**data)
            save_json(valid_model.model_dump())
    except FileNotFoundError:
        print ("The file don't exist")
    except json.JSONDecodeError:
        print ("The file is not a valid JSON")
    except ValidationError:
        print ("The JSON doesn't have correct format")

read_json() 
