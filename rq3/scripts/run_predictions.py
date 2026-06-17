import json
import re
import time
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from rq3.prompt import optimized_prompt


# Settings
SOURCE_DIR = Path("<PATH_TO_P5_SOURCE_FILES>")
OUTPUT_DIR = Path("<PATH_TO_OUTPUT_FOLDER>")

MODEL_NAME = "qwen3-coder-30b-fp8"
BASE_URL = "http://localhost:8000/v1"
SYSTEM_PROMPT = "You are a helpful coding assistant."

MAX_TOKENS = 512
TEMPERATURE = 0
MAX_RETRIES = 3
SAVE_EVERY = 25
MAX_FILES_TO_RUN = None  # use an integer for testing, e.g. 100


ALLOWED_LABELS = {
    "entities": {
        "processed_audio",
        "processed_image",
        "processed_text",
        "synthesized_sound",
        "synthesized_text",
        "synthesized_image",
        "randomness",
    },
    "interaction": {"yes", "no"},
    "outcome": {"visual", "auditory", "static", "time_based"},
}


# JSON extraction + validation
def extract_json(raw_output):
    text = raw_output.strip()

    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    return None


def clean_prediction(prediction):
    if not isinstance(prediction, dict):
        return None

    cleaned = {}

    for group in ["entities", "interaction", "outcome"]:
        values = prediction.get(group, [])

        if isinstance(values, str):
            values = [values]

        if not isinstance(values, list):
            return None

        cleaned[group] = [
            value
            for value in values
            if value in ALLOWED_LABELS[group]
        ]

    if len(cleaned["interaction"]) != 1:
        return None

    time_labels = [
        label
        for label in cleaned["outcome"]
        if label in {"static", "time_based"}
    ]

    modality_labels = [
        label
        for label in cleaned["outcome"]
        if label in {"visual", "auditory"}
    ]

    if len(time_labels) != 1:
        return None

    if len(modality_labels) == 0:
        return None

    if "auditory" in modality_labels and "time_based" not in time_labels:
        return None

    cleaned["outcome"] = modality_labels + time_labels

    return cleaned


# Classification
def classify_source_code(client, source_code):
    user_prompt = (
        optimized_prompt
        + "\n\nSource code to classify:\n"
        + "```javascript\n"
        + source_code
        + "\n```"
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )

            raw_output = response.choices[0].message.content
            parsed_output = extract_json(raw_output)
            cleaned_prediction = clean_prediction(parsed_output)

            if cleaned_prediction is not None:
                return cleaned_prediction, None

            last_error = f"invalid_json_or_schema: {raw_output}"

        except Exception as error:
            last_error = f"api_error: {error}"
            time.sleep(min(2 * attempt, 10))

    return None, last_error


# Run
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

predictions_file = OUTPUT_DIR / "predictions.json"
errors_file = OUTPUT_DIR / "errors.jsonl"

if predictions_file.exists():
    with predictions_file.open("r", encoding="utf-8") as file:
        predictions = json.load(file)
else:
    predictions = []

already_classified = {
    item["file_path"]
    for item in predictions
}

source_files = [
    path
    for path in SOURCE_DIR.rglob("*")
    if path.is_file()
]

source_files = [
    path
    for path in source_files
    if str(path.relative_to(SOURCE_DIR)) not in already_classified
]

if MAX_FILES_TO_RUN is not None:
    source_files = source_files[:MAX_FILES_TO_RUN]

client = OpenAI(
    base_url=BASE_URL,
    api_key="EMPTY",
)

print(f"Model: {MODEL_NAME}")
print(f"Source directory: {SOURCE_DIR}")
print(f"Output directory: {OUTPUT_DIR}")
print(f"Already classified: {len(already_classified)}")
print(f"Files selected for this run: {len(source_files)}")

success_count = 0
error_count = 0

with errors_file.open("a", encoding="utf-8") as error_file:
    for index, file_path in enumerate(
        tqdm(source_files, desc="Classifying files", unit="file"),
        start=1,
    ):
        relative_path = str(file_path.relative_to(SOURCE_DIR))

        with file_path.open("r", encoding="utf-8", errors="ignore") as file:
            source_code = file.read()

        if not source_code.strip():
            error_file.write(
                json.dumps(
                    {
                        "file_path": relative_path,
                        "error": "empty_file",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            error_count += 1
            continue

        prediction, error = classify_source_code(
            client=client,
            source_code=source_code,
        )

        if prediction is not None:
            predictions.append(
                {
                    "file_path": relative_path,
                    "predicted_labels": prediction,
                }
            )
            success_count += 1

        else:
            error_file.write(
                json.dumps(
                    {
                        "file_path": relative_path,
                        "error": error,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            error_count += 1

        if index % SAVE_EVERY == 0:
            with predictions_file.open("w", encoding="utf-8") as file:
                json.dump(predictions, file, indent=2, ensure_ascii=False)

with predictions_file.open("w", encoding="utf-8") as file:
    json.dump(predictions, file, indent=2, ensure_ascii=False)

print("\nDone.")
print(f"Successful predictions in this run: {success_count}")
print(f"Errors in this run: {error_count}")
print(f"Total predictions saved: {len(predictions)}")
print(f"Predictions file: {predictions_file}")
print(f"Errors file: {errors_file}")