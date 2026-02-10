import json
from pathlib import Path

def create_log_files(api_key: str, input_file: str, response_key: str, data_key: str, output_file: str) -> None:
    queue_log = {
        "api_key": api_key,
        "input_file": input_file,
        "output_file": output_file,
        "response_key": response_key,
        "data_key": data_key,
        "batches": []
    }
    with open("batch_queue_log.json", 'w') as f:
        json.dump(queue_log, f, indent=4)

    with open("batch_log.json", 'w') as log_file:
        json.dump([], log_file)

def log_batch_request(batches: list) -> None:
    with open("batch_queue_log.json", 'r') as f:
        log = json.load(f)
    
    log["batches"] = batches

    with open("batch_queue_log.json", 'w') as f:
        json.dump(log, f, indent=4)

def log_response_history(action: str, batch_file: str, batch_id: str=None, file_id: str=None, status: str=None) -> None:
    #This is added as a safety check, but if this is called from send_batch_request, an empty list will be initialized before everything starts.
    with open("batch_log.json", 'r') as f:
        log = json.load(f)

    lsn = len(log) + 1
    log_entry = {
        "LSN": lsn,
        "action": action,
        "batch_file": batch_file,
        "batch_id": batch_id,
        "file_id": file_id,
        "status": status
    }

    log.append(log_entry)

    with open("batch_log.json", 'w') as f:
        json.dump(log, f, indent=4)
