def create_err_response(message: str) -> dict:
    return {
        "error": True,
        "message": message
    }


def create_ok_response(data) -> dict:
    return {
        "data": data,
        "error": False,
        "message": ""
    }
