# Batch Requests
Batch_Requests is a convenient way to use the openAI batched api to process large amounts of data in an automated manner.

## Update 02/2026
The easiest way to use this is actually just to depend on `send_batch_requests.py` as well as `recover_batch_requests.py`. The 2 scripts have been updated and are generally robust for captioning as well as recovery. Here is more information on how to use both scripts:

### `send_batch_requests.py`
There are 3 necessary inputs as well as 3 optional inputs for this file.
- `--input_file / -i` The input file that is meant to be processed.
- `--step / -s` The step that is meant to be performed. This will reference a key in the config file.
- `--config / -c` This is the [config file](#configuration-file) that you are referencing. It is a `.yaml` file.
- `--output_file / -o` The output file that the processed data will be written to. Defaults to the input file if this is not specified.
- `--response_key / -r` This is the key that the response will be recorded under. It will default to looking under config for `response_key` if it is not provided. Note that this behaviour is only implemented under `send_batch_request.py`, and the actual batch_requests api will have to be modified if you want this to work without using `send_batch_requests.py`.
- `--data_key / -d` The key that will be used by the OpenAI batched api to recognise each data point. Defaults to `image_path`, which should be distinct assuming data is clean and deduplicated. Can be reassigned as needed.

example:
```
uv run send_batch_request.py -i cna_scraper/scraper_logs/filtered_cna_images.json -s article_filter -c gpt_captioning_config.yaml -d image_path
```

### `recover_batch_requests.py`
Used to recover when the sending script crashes. Relies on functions from `send_batch_requests.py`. This is mean to be run without any inputs, but it relies on the log files created when `send_batch_requests.py` is called.  
Note that there is a known bug where upon completion, the very last entry does not get popped, and as such running recover on a completed script will result in the last request that has been queued up to get resent again. 

### Additional Notes about creation and recovery systems
When running `send_batch_requests.py` a few `.jsonl` files will be created to facilitate the running of the script. A `.jsonl` representing the each batch will be created in the same directory as the input file, and 2 `.json` files will be created to act as the logging tables for recovery. It is highly not recommended to modify these unless you understand what each element does as they are crucial for running the scripts. 

### Quirks of batched api and image url
Due to the fact that the batched api has a 200mb limit for a batch, it is recommended to use permanent and public links to images when captioning is performed. If the images were pulled from a stable host like CNA, Straits times or an image hosting site, that can be your image url. Otherwise the cheapest way to get a large number of permanent image urls is to abuse github and link the images from there. Note that the git repo has to be public otherwise the api will be served a 403 and the pipeline will not work.

## Input formats and Instructions
`batch_requests` can generally be used with any data in the json format, but a `yaml` based config will have to be made for the object. Note that the file formats are just suggestions for ease of reading, in the program, the user will have to parse the files themselves and pass it into the program as a python list or dictionary object. Examples can be seen under `./config/`  
For the default configuration, it is made to be optimised for multimodal data containing both pictures and text and data should be given in the json format as a list of hash tables and config files should be given in the yaml format as a hash table.  
A config file can be made for each specific use case. Note that the word `question` is a special case for the batch request maker as the current format used for questions requires the creation of a `dialog_history` key in the input data. For more information see the section on [`batch_request_maker`](#batch_request_makerpy)
Below are the keys required for each input.
### Configuration file
The configuration file is a yaml file with each piece of important information as a key that will be used by the system. With the current implementation, it contains the prompts for each step as well as the api key and model name for access.  
Here are the important keys that will be used by the system.
- `model`: the name of the model that will be used.
- `api_key`: the openAI api key that will be used.

Prompts exist as a nested hash table for each step that will be executed. Each prompt should have a `system` and `user` key representing the system prompt and the user prompt.  
In the system prompt, there should be no placeholders.  
In the user prompt, placeholders are used to insert information unique to each data point.  
Additionally, the key `is_multimodal` can be used to denote that the user does not want to send an image along with the prompts. By default if this key is skipped, `is_multimodal` will default to `True` and an image will be sent along with the prompt.  
Finally, an optional `response_key` can be added to be used as the key the script will save the response under in the dataset. If this is excluded, it should be passed to the script in some way or another.

### batch_request_checker.py
Used to check batches that have already been sent to process.
Useful for manually retrieving files dropped by the system or checking on their status without using curl.
The main method to be called here is `check_request`. It takes in 2 inputs and returns an openAI batch object. For more information see [the official openAI documentation](https://platform.openai.com/docs/api-reference/batch/object). Here are the relevant fields for `check_request`:
- `api_key`: a String representing the openAI api key used to make the requests.
- `batch_id`: a string representing the batch_id that is to be checked.

### batch_request_logger.py
Used to log the current activity of the batches that have been sent. Does not currently work when sending in parallel, but it generally should not matter due to the lack of capacity to send more than 1 batch of 1000 data points in at a single time.  
Call this in a send_batch_request file for easy tracking of the current status of each file. This is not to be used manually.  
An example implementation of this recovery can be seen in `./example/recover_batch_request.py`
The 3 main methods used to create log files are `create_log_files`, `log_batch_request` and `log_response_history`.  
`create_log_files` stores a copy of all the important information required to check and complete any ongoing requests.  
`log_batch_request` should be called after each batch request has been completed and it stores and updates the list of batches that have yet to be sent.
`log_response_history` is called between each step so that recovery can begin at the relevant step instead of needing to resend a whole batch each time the system crashes.

### batch_request_maker.py
Used to batch and prepare requests into a jsonl format to be sent to the openAI batched api for processing. 
By default, any prompt will be dynamically fitted with data if it exists. If 5 consecutive data points do not have the fields required for the prompt, it will throw a `ValueError` and break to ensure that incomplete prompts are not sent for processing.  
The method to be called in this file is `make_requests`. Make requests has 4 input fields and it returns a list of dictionaries that will be saved as a `jsonl` object that can be sent as a batch of requests to the openAI batched api. Here are the inputs of `make_requests`:
- `config_data`: the config file loaded in the form of a dictionary.
- `step`: a String that can be used to reference a key in the `config_data` dictionary that represents the system and user prompt to be selected.
- `input_data`: a list of dictionaries that contain the data points that are to be processed.
- `input_key`: a string that refers to the primary key of each data point. It defaults to `image_path`.  

`question` exists as a special case due to the past implementation of question_answer pair generation, and as such the word `question` should not be used unless you want this specific interaction to occur:
- The config file should have these fields: `dialog_history`, `context`, `image_url`
- The data should have these fields with these representations:
  - `dialog_history`: This is the only optional field, it will be instantiated when the first question is made. It contains every past question and answer in the form of a string.
  - `cleaned_caption`: This refers to a caption cleaned of pii in the form of a string. It will default to a blank string if it does not exist.
  - `generated_caption`: A string object that contains a descriptive caption describing the image.
  - `image_url`: A string containing a stable url to the image to be processed. This is used to pass the image to the model.
The reason for this implentation is that it will ignore the existence of blank fields and proceed, unlike with the standard implementation where a `ValueError` will be thrown if there are blank fields provided.

### batch_request_retriever.py
There are 4 main methods that compose `batch_request_retriever`and it is used to retrieve and write the data to the data file.
`retrieve_requests` retrieves and returns the text content of the file that is to be retrieved. It has 2 inputs:
- `api_key`: a String representing the openAI api key used to make the requests.
- `file_id`: a string representing the file_id that is to be retrieved.  
`parse_response`is a useful parser that helps to deal with the data output by retrieve requests. It returns the the data in a dictionary with the objects Primary Key as the key and the string output as the value. If there are any changes to the way the openAI batched api works, this will likely have to be changed to handle the new output. It takes in the following inputs:
- `response_text`: the response text provided by `retrieve_requests`. This is a string object.
`handle_captions` is the default way of writing the output back to disk. It will overwrite a given dictionary to include the newly generated data taht has been provided by the API. Here are the inputs that it requires:
- `input_data` is a dictionary that represents the original data set.
- `response_data` is the dicitonary output by `parse_response`. The primary key in `response_data` and `input_data` should match, or this method will not do anything.
- `response_key` is a string that will be used as the key to reference the data generated by the api call.
- `data_key` is a string that represents the primary key for `input_data` and `response_data`
`handle_qna` is a special case for question answer pairs, it does what `handle_captions` does but logs questions and answers in a nested dictionary as well as adds each output to the `dialog_history`so that it can be used for further prompting. It has the same inputs as `handle_captions`

### batch_request_sender.py
There is 1 main method in `batch_request_sender` that is used to send batch_requests. It returns [an openAI batch object](https://platform.openai.com/docs/api-reference/batch/object) that can be used for subsequent processing. It has the following inputs:
- `api_key`: a string representing the api key that will be used to send the batch request
- `input_file`: a string representing the path to a `jsonl` file that contains the data that will be sent as the current batch.

### batch_request_splitter.py
There are 2 main methods that can be used depending on the users needs. They do the same thing, but one works with data that has yet to be written while the other reads from a `jsonl` file.
`split_jsonl_file` reads data from a given `jsonl` file and splits it into smaller batches of maximum size 1000 so that the cap for the API limits are not hit as quickly. It has 2 input variables:
- `input_file`: a string representing the path to the `jsonl` object that is to be split up.
- `step`: a string representing the step that is to be performed. This does not have to be exact as it is just used to name the file for easier identification in the future.
`split_jsonl_list` reads data from a given list instead of a file. This is useful when calling methods in succession as can be seen in `./example/send_batch_request.py` where requests are made and sent without writing to disk. Here are the inputs required:
- `input_list` a list representing the jsonl object. This happens to be what is returned by [`batch_request_maker`](#batch_request_makerpy)
- `input_path`: a string that will represent the path to the directory that the files will be written in. if no input_path is provided it will default to "."
- `step`: a string representing the step that is to be performed. This does not have to be exact as it is just used to name the file for easier identification in the future.

### batch_request_viewer.py
This is just a utility file that can be used to view the status of the last batches that were sent to be processed. It will generally not be called when running the program as it does not interact with any batches except as a checker. Here are the inputs for it:
- `config_file`: a string representing the path to the configuration file that contains the openAI api key used to send the batches.
- `limit`: an integer representing the number of past batches that will be shown. By default this value will be 10.
If the user would rather use `curl`, here's the `curl` equivalent for this file.
```
curl https://api.openai.com/v1/batches \
  -H "Authorization: Bearer API_KEY_HERE" | \
  jq '[.data[] | select(.status == "in_progress")][10]'
```
Note that the status and limit can be customised to suit the users needs.
