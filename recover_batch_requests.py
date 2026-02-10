import json

from send_batch_request import (
    send_batch_request,
    await_batch_request,
    retrieve_batch_request
)
from batch_requests.batch_request_logger import log_batch_request

if __name__ == "__main__":
    with open("batch_log.json", 'r') as f:
        batch_log = json.load(f)
    
    with open("batch_queue_log.json", 'r') as f:
        batch_queue_log = json.load(f)

    api_key = batch_queue_log.get("api_key")
    input_file = batch_queue_log.get("input_file")
    output_file = batch_queue_log.get("output_file")
    response_key = batch_queue_log.get("response_key")
    data_key = batch_queue_log.get("data_key")
    batches = batch_queue_log.get("batches")

    with open(input_file, "r") as f:
        input_data = json.load(f)

    if batch_log:
        last_action = batch_log[-1].get("action")
        last_action_status = batch_log[-1].get("status")
    else:
        last_action = None
        last_action_status = None

    if last_action == "send_batch_request" and last_action_status == "starting":
        pass # should probably remove this log status as it should not be needed since the end result is the same either ways
    elif last_action == "send_batch_request" and last_action_status == "in_progress":
        current_batch = batches.pop(0)
        batch_id = batch_log[-1].get("batch_id")
        await_batch_request(api_key, current_batch, input_data, response_key, data_key, output_file, batch_id=batch_id)
    elif last_action == "retrieving_batch_request" and last_action_status == "starting":
        current_batch = batches.pop(0)
        batch_id = batch_log[-1].get("batch_id")
        file_id = batch_log[-1].get("file_id")
        retrieve_batch_request(api_key, current_batch, input_data, response_key, data_key, output_file, batch_id, file_id)
    elif last_action_status == "retrieving_batch_request" and last_action_status == "completed":
        pass # No need to do anything more for this batch, just proceed to the remaining ones

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

    
    