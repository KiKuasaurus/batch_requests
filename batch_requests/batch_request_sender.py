from openai import OpenAI
import yaml
import argparse
import json
from rich import print_json

def send_requests(api_key: str, input_file: str):
    client = OpenAI(api_key=api_key)

    batch_input_file = client.files.create(
        file = open(input_file, 'rb'),
        purpose = 'batch'
    )

    batch_input_file_id = batch_input_file.id

    batch = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )

    return batch

def main(config: str, input_file: str):
    with open(config, 'r') as file:
        config_data = yaml.safe_load(file)
    
    api_key = config_data.get('api_key')
    if not api_key:
        raise ValueError("API key is required in the configuration file.")

    batch = send_requests(api_key, input_file)

    print_json(json.dumps(batch.to_dict(), indent=4))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a batch request for OpenAI API.")
    parser.add_argument('--config', '-c', type=str, required=True, help='Path to the configuration file.')
    parser.add_argument('--input_file', '-i', type=str, required=True, help='Path to the input file for batch processing.')

    args = parser.parse_args()

    main(args.config, args.input_file)
