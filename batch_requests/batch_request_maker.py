import argparse
import json
import os
from string import Formatter
from tqdm import tqdm
from typing import List, Dict, Any
import yaml

from .batch_request_splitter import split_jsonl_list

def make_requests(config_data: dict, step:str, input_data: list, input_key: str="image_path") -> list:

    step_prompt = config_data.get(step, None)

    if not step_prompt:
        raise ValueError("Step prompts are not in the dictionary")

    model = config_data.get('model')
    if not model:
        raise ValueError("Model not specified in config file.")
    
    if "question" in step:
        # There is a separate check for question as there is a counter in the dynamic promptmaker to check if a field is missing.
        # The first question generated will initialize 2 new fields (qna, dialog history) so it will be handled separately to ensure that empty batches of requests are not sent.
        # The consequence of this is that the question prompt will be more fixed unless the user comes up with a different way to format the dialog history field.
        output_data = generate_question(input_data, step_prompt, model, input_key)
    else:
        output_data = dynamic_promptmaker(input_data, step_prompt, model, input_key)
    
    return output_data

def dynamic_promptmaker(input_data: List[Dict[str, Any]], prompt: Dict[str, str], model: str, input_key: str) -> List[Dict[str, Any]]:
    sysprompt = prompt['system']
    userprompt = prompt['user']
    is_multimodal = prompt.get('is_multimodal', True) # Since this is generally meant for multimodal captioning, we default to true.

    formatter = Formatter()

    required_fields = []
    for literal_text, field_name, format_spec, conversion in formatter.parse(userprompt):
        if field_name is not None:
            required_fields.append(field_name)
    required_fields = set(required_fields)

    requests = []
    failed_tries = 0 # If the input data does not have the required fields more than 5 times, we break and move on. 

    for data in tqdm(input_data, desc="Making prompts"):
        file_key = data[input_key]
        if 'mp4' in file_key or 'gif' in file_key:
            continue
        # This is a check implemented to remove images that have already been filtered.
        # It mirros the check made for question, so if processing is done by any process other than question generation, dropped images do not get processed.
        # It is also why in the documentation it is suggested to use 'REMOVE_IMAGE' specifically, since it keeps things consistent, while being unlikely to appear in an actual caption.
        if 'REMOVE_IMAGE' in data.get('generated_caption', ''):
            continue
        try:
            formatted_userprompt = userprompt.format(**data)
        except KeyError as e:
            print("Missing field: ", e)
            failed_tries += 1
            if failed_tries == 5:
                raise ValueError("Input data is missing required fields for the prompt. Please check the input data and prompt.")
            else:
                continue

        failed_tries = 0
        
        if is_multimodal:
            image = data["image_url"]

            batch_request = {
                "custom_id": file_key,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sysprompt.strip()},
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": image}},
                            {"type": "text", "text": formatted_userprompt}
                        ]}
                    ]
                }
            }
            requests.append(batch_request)
        else:
            batch_request = {
                "custom_id": file_key,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sysprompt.strip()},
                        {"role": "user", "content": formatted_userprompt}
                    ]
                }
            }
            requests.append(batch_request)
    
    return requests

def generate_question(input_data: List[Dict[str, Any]], prompt: Dict[str, str], model: str, input_key: str) -> List[Dict[str, Any]]:
    sysprompt = prompt['system']
    userprompt = prompt['user']
    requests = []

    for i, data in enumerate(tqdm(input_data, desc=f"Generating Questions")):
        if "REMOVE_IMAGE" in data["generated_caption"]:
            continue
        file_key = data[input_key]

        dialogue_history = data.get('dialogue_history', '')
        context = data.get('cleaned_caption', '') + "\n" + data.get('generated_caption', '')

        image = data["image_url"]


        batch_request = {
            "custom_id": file_key,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "messages": [
                    {"role": "system", "content": sysprompt.strip()},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": image}},
                        {"type": "text", "text": userprompt.format(dialogue_history=dialogue_history, context=context).strip()}
                    ]}
                ]
            }
        }

        requests.append(batch_request)

    return requests

def main(config: str, step: str, input_file: str=None, output_file: str=None):
    with open(config, 'r') as file:
        config_data = yaml.safe_load(file)

    if input_file:
        with open(input_file, 'r') as f:
            input_data = json.load(f)
    else:
        raise ValueError("Input file is required.")

    output_data = make_requests(config_data, step, input_data)

    if output_file:
        with open(output_file, 'w') as f:
            for item in output_data:
                f.write(json.dumps(item) + '\n')

    input_path = os.path.dirname(input_file)
    if len(output_data) > 1000:
        split_jsonl_list(input_list=output_data, input_path=input_path, step=step)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate data using OpenAI API.")
    parser.add_argument('--config', '-c', type=str, required=True, help='Path to the configuration file.')
    parser.add_argument('--input_file', '-i', type=str, help='Path to the input JSON file.')
    parser.add_argument('--output_file', '-o', type=str, required=False, help='Path to the output JSONL file.')
    parser.add_argument('--step', '-s', type=str, help='Step to perform.')

    args = parser.parse_args()
    main(args.config, args.step, args.input_file, args.output_file)