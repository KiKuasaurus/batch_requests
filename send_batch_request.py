from urllib import response
import yaml
import json
import argparse
import time
import os

from batch_requests.batch_request_checker import check_request
from batch_requests.batch_request_logger import (
    create_log_files, 
    log_batch_request, 
    log_response_history
)
from batch_requests.batch_request_maker import make_requests
from batch_requests.batch_request_retriever import (
    retrieve_requests,
    parse_response,
    handle_captions,
    handle_qna
)
from batch_requests.batch_request_sender import send_requests
from batch_requests.batch_request_splitter import split_jsonl_list

def send_batch_request(api_key: str, batch_file: str, input_data: dict, response_key: str, data_key: str, output_file: str):
    log_response_history(action="send_batch_request",batch_file=batch_file ,batch_id=None, file_id=None, status="starting")

    batch_id = None
    while True:
        print("sending batch request...")
        batch = send_requests(api_key, batch_file)
        time.sleep(60)
        current_status = check_request(api_key, batch.id)
        status = current_status.status
        print(f"current status: {status}")
        if status == "in_progress" or status == "completed" or status == "finalizing":
            batch_id = batch.id
            break
        elif status == "validating":
            # nested loop to keep checking if it has been validated.
            for i in range(1000):
                time.sleep(30)
                current_status = check_request(api_key, batch.id)
                status = current_status.status
                print(f"current status: {status}")
                if status == "in_progress" or status == "completed" or status == "finalizing":
                    batch_id = batch.id
                    break
                elif status == "failed":
                    break
                elif status != "validating":
                    break
            if batch_id == batch.id:
                break
    
    await_batch_request(api_key, batch_file, input_data, response_key, data_key, output_file, batch_id)

def await_batch_request(api_key: str, batch_file: str, input_data: dict, response_key: str, data_key: str, output_file: str, batch_id: str) -> None:
    log_response_history(action="send_batch_request", batch_file=batch_file, batch_id=batch_id, file_id=None, status="in_progress")

    print("request successfully sent, waiting for completion...")
    file_id = None
    while True:
        batch = check_request(api_key, batch_id)
        print(f"current status: {batch.status}")
        if batch.status == "completed":
            file_id = batch.output_file_id
            break
        time.sleep(60)

    retrieve_batch_request(api_key, batch_file, input_data, response_key, data_key, output_file, batch_id, file_id)

def retrieve_batch_request(api_key: str, batch_file: str, input_data: dict, response_key: str, data_key: str, output_file: str, batch_id: str, file_id: str) -> None:
    log_response_history(action="retrieving_batch_request",batch_file=batch_file, batch_id=batch_id, file_id=file_id, status="starting")

    print(f"batch {batch_file} completed, writing to file")
    response_text = retrieve_requests(api_key, file_id)

    parsed_outputs = parse_response(response_text)

    original_data = input_data
    if 'question' in response_key or 'answer' in response_key:
        output_data = handle_qna(original_data, parsed_outputs, response_key, data_key)
    else:
        output_data = handle_captions(original_data, parsed_outputs, response_key, data_key)

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=4)
    log_response_history(action="retrieving_batch_request",batch_file=batch_file, batch_id=batch_id, file_id=file_id, status="completed")

def make_and_send_batch_request(input_file: str, step: str, response_key: str=None, output_file: str=None, config_path: str='batch_requests/config/gpt_captioning_config.yaml', data_key: str="image_path"):
    with open(config_path, 'r') as file:
        config_data = yaml.safe_load(file)

    with open(input_file, 'r') as f:
        input_data = json.load(f)

    response_key = response_key or config_data.get(step, {}).get("response_key", "")
    if not response_key:
        raise ValueError("Response key has to be in either the config or passed as an input parameter")

    requests_data = make_requests(config_data=config_data, step=step, input_data=input_data, input_key=data_key)
    batches = split_jsonl_list(input_list=requests_data, input_path=os.path.dirname(input_file), step=step)

    if output_file == None:
        output_file = input_file

    api_key = config_data.get('api_key')
    create_log_files(api_key, input_file, response_key, data_key, output_file)

    while batches:
        log_batch_request(batches)
        batch = batches.pop(0)
        send_batch_request(api_key=api_key, 
                                         batch_file=batch,
                                         input_data=input_data,
                                         response_key=response_key,
                                         data_key=data_key,
                                         output_file=output_file
                                        )

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process batch requests")
    parser.add_argument("--input_file", '-i', type=str, required=True, help="Path to the input file")
    parser.add_argument("--output_file", '-o', type=str, required=False, help="Path to the output file")
    parser.add_argument("--step", '-s', type=str, required=True, help="Step to perform")
    parser.add_argument("--response_key", '-r', type=str, required=False, help="Response key to use")
    parser.add_argument("--config", '-c', type=str, required=True, help="Path to the config file")
    parser.add_argument("--data_key", "-d", type=str, required=False, help="The key used to identify each data point")
    args = parser.parse_args()

    if not args.data_key:
        args.data_key = "image_path"
    make_and_send_batch_request(args.input_file, args.step, args.response_key, args.output_file, args.config, args.data_key)
