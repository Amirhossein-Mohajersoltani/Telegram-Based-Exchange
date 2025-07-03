def create_message(status:bool, status_info:str, key:str=None, additional_data:dict=None, command:str=None):
    if additional_data is None:
        additional_data = {}
    return [{
        'status': status,
        'status_info': status_info,
        'key': key,
        'additional_data': additional_data,
        "command": command
    }]