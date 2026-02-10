from openai import OpenAI
import yaml
import argparse
import json
import os

def retrieve_requests(api_key: str, file_id: str=None):
    client = OpenAI(api_key=api_key)

    if not file_id:
        raise ValueError("Batch ID is required to retrieve the batch request.")

    file_response = client.files.content(file_id)
    
    return file_response.text

def parse_response(response_text: str):
    parsed_outputs = {}
    for line in response_text.splitlines():
        try:
            record = json.loads(line)
            custom_id = record.get("custom_id")
            message = (
                record.get("response", {})
                    .get("body", {})
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )

            if message is None:
                continue
            try:
                clean_text = message.replace("```json", "").replace("```", "").replace("\n", "").strip()
                parsed_outputs[custom_id] = json.loads(clean_text)
            except json.JSONDecodeError:
                parsed_outputs[custom_id] = message
        except json.JSONDecodeError:
            print(f"Error decoding JSON for line: {line}")
    
    return parsed_outputs

def handle_captions(input_data: dict, response_data: dict, response_key: str, data_key: str) -> dict:
    for item in input_data:
        image_path = item.get(data_key)
        if image_path in response_data:
            item[response_key] = response_data[image_path]
    return input_data

def handle_qna(input_data: dict, response_data: dict, response_key: str, data_key: str) -> dict:

    if 'question' in response_key:
        step_type = 'question'
    elif 'answer' in response_key:
        step_type = 'answer'

    for item in input_data:
        image_path = item.get(data_key)
        if image_path in response_data:
            current_qna = len(item.get('question_and_answers', []))  // 2
            if 'dialogue_history' not in item:
                item['dialogue_history'] = f"{step_type}_{current_qna}: {response_data[image_path]}\n"
            else:
                item['dialogue_history'] += f"{step_type}_{current_qna}: {response_data[image_path]}\n"
            if 'question_and_answers' not in item:
                item['question_and_answers'] = {f'{step_type}_{current_qna}': response_data[image_path]}
            else:
                item['question_and_answers'][f'{step_type}_{current_qna}'] = response_data[image_path]
    
    return input_data
            
def main(config_path: str, file_id: str=None, input_file: str=None, output_file: str=None, response_key: str=None, data_key: str="image_path"):
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)

    api_key = config.get('api_key')
    if not api_key:
        raise ValueError("API key is required in the configuration file.")

    response_text = retrieve_requests(api_key, file_id)

    parsed_outputs = parse_response(response_text)
    
    try:
        with open(input_file, 'r') as f:
            input_data = json.load(f)
    except FileNotFoundError:
        input_data = []

    if 'question' in response_key or 'answer' in response_key:
        input_data = handle_qna(input_data, parsed_outputs, response_key, data_key)
    else:
        input_data = handle_captions(input_data, parsed_outputs, response_key, data_key)

    if output_file == None:
        output_file = input_file

    with open(output_file, 'w') as f:
        json.dump(input_data, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve a batch request from OpenAI API.")
    parser.add_argument('--config', '-c', type=str, required=True, help='Path to the configuration file.')
    parser.add_argument('--file_id', '-f', type=str, required=True, help='ID of the file to retrieve.')
    parser.add_argument('--input_file', '-i', type=str, required=False, help='Path to the input file for batch processing.')
    parser.add_argument('--output_file', '-o', type=str, required=False, help='Path to save the output file.')
    parser.add_argument('--response_key', '-r', type=str, required=False, help='Key to store the response in the input data.')

    args = parser.parse_args()

    main(args.config, args.file_id, args.input_file, args.output_file, args.response_key)
