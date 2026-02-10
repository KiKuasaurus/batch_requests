from openai import OpenAI
import yaml
import json
from rich import print_json

def check_request(api_key: str, batch_id: str=None):

    client = OpenAI(api_key=api_key)

    batch = client.batches.retrieve(batch_id)
    
    return batch

def main(config: str, batch_id: str):
    with open(config, 'r') as file:
        config_data = yaml.safe_load(file)
    
    api_key = config_data.get('api_key')
    if not api_key:
        raise ValueError("API key is required in the configuration file.")

    batch = check_request(api_key, batch_id)

    print_json(json.dumps(batch.to_dict(), indent=4))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Retrieve a batch request from OpenAI API.")
    parser.add_argument('--config', '-c', type=str, required=True, help='Path to the configuration file.')
    parser.add_argument('--batch_id', '-b', type=str, required=True, help='ID of the batch request to retrieve.')

    args = parser.parse_args()

    main(args.config, args.batch_id)