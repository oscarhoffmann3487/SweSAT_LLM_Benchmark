import json
import sys
from typing import Any
from inspect_ai.dataset import hf_dataset, Sample
from inspect_ai.solver import multiple_choice
from inspect_ai.scorer import choice
from inspect_ai.model import GenerateConfig
from inspect_ai import Task, eval
from inspect_ai.solver import system_message

def record_to_sample(record: dict[str, Any]) -> Sample:
    """
    Convert one JSON row into a `Sample` for inspect_ai.
    If 'article' is present, we include it in the prompt.
    Otherwise, we just use the question.
    """
    if "article" in record and record["article"]:
        full_input = f"{record['article']}\n\nFråga: {record['question']}"
    else:
        full_input = record["question"]

    return Sample(
        input=full_input,
        choices=record["options"],
        target=record["answer"],  # e.g. "A","B","C","D"
        metadata={
            "id": record["id"],
            "type": record["type"],
            "article": record.get("article", None),
        },
    )

def get_custom_dataset(json_file: str, shuffle: bool = False):
    """
    Let `hf_dataset` load our local JSON file and automatically
    wrap it as an inspect_ai-compatible Dataset.
    """
    dataset = hf_dataset(
        path="json",                     
        split="train",                   
        data_files={"train": json_file},  
        sample_fields=record_to_sample,
        shuffle=shuffle,
        seed=42,
    )
    return dataset

def custom_task(json_file: str) -> Task:
    """
    Create a Task that uses multiple_choice solver on your custom JSON data.
    """
    dataset = get_custom_dataset(json_file, shuffle=True)
    return Task(
        dataset=dataset,
        solver=[
            # 1) First run system_message
            system_message(SYSTEM_MESSAGE),
            # 2) Then run multiple_choice
            multiple_choice(cot=False),
        ],

        scorer=choice(),
        config=GenerateConfig(temperature=0.5),
    )


if __name__ == "__main__":
    models_to_compare = [
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "anthropic/claude-3-5-haiku-latest",
        "anthropic/claude-3-5-sonnet-latest"
    ]
    
    #data = "en_mek"
    data = sys.argv[1]
    with open("sys_prompt.json", "r", encoding="utf-8") as f:
        messages = json.load(f)

    SYSTEM_MESSAGE = messages[data]
    eval(custom_task("data/" + data + ".json"), model=models_to_compare)
