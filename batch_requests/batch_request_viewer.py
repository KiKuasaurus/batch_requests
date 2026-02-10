from openai import OpenAI
import yaml
import argparse

def main(config_file: str, limit: int = 10):
    with open(config_file, 'r') as file:
        config_data = yaml.safe_load(file)
    
    api_key = config_data.get('api_key')
    if not api_key:
        raise ValueError("API key is required in the configuration file.")
    
    client = OpenAI(api_key=api_key)

    client.batches.list(limit)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List batch requests for OpenAI API.")
    parser.add_argument('--config', '-c', type=str, required=True, help='Path to the configuration file.')

    args = parser.parse_args()
    main(args.config)