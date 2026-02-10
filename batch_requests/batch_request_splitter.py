import json
import argparse
import os
import math

def split_jsonl_file(input_file: str, step: str):
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    
    print(len(lines))
    print(math.ceil(len(lines) / 1000))

    num_batches = math.ceil(len(lines) / 1000)
    batch_size = len(lines) // num_batches

    input_path = os.path.dirname(input_file)

    batches = []

    for i in range(num_batches):
        start = i * batch_size
        end = (i + 1) * batch_size if i < num_batches - 1 else len(lines)
        request_batch = lines[start:end]
        batch_file = f"{input_path}/batch_{step}_{i + 1}.jsonl"
        with open(batch_file, 'w') as f:
            for request in request_batch:
                f.write(request.strip()  + '\n')
        print(f"Batch {i + 1} written to {batch_file}")
        batches.append(batch_file)

    return batches

def split_jsonl_list(input_list: list, input_path: str, step: str) -> list:
    lines = input_list

    print(len(lines))
    print(math.ceil(len(lines) / 1000))

    num_batches = math.ceil(len(lines) / 1000)
    batch_size = len(lines) // num_batches

    batches = []

    if not input_path:
        input_path = "."

    for i in range(num_batches):
        start = i * batch_size
        end = (i + 1) * batch_size if i < num_batches - 1 else len(lines)
        request_batch = lines[start:end]
        batch_file = f"{input_path}/batch_{step}_{i + 1}.jsonl"
        with open(batch_file, 'w') as f:
            for request in request_batch:
                f.write(json.dumps(request) + '\n')
        print(f"Batch {i + 1} written to {batch_file}")
        batches.append(batch_file)

    return batches

# Example usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split a JSONL file into two parts.")
    parser.add_argument('--input_file', '-i', type=str, help='Path to the input JSONL file.')
    parser.add_argument('--step', '-s', type=str, help='Step name for the batch files.')

    args = parser.parse_args()
    split_jsonl_file(args.input_file, args.step)
