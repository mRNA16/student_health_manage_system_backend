"""
utils for generating api responses
"""
import json
from enum import Enum, unique
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods

@unique
class ErrorCode(Enum):
    """
    api error code enumeration
    """
    # success code family
    SUCCESS = 0

    # bad request family
    INVALID_REQUEST_ARGS = 400
    BAD_REQUEST_ERROR = 400_00
    INVALID_REQUEST_ARGUMENT_ERROR = 400_01
    REQUIRED_ARG_IS_NULL_ERROR = 400_02
    
    # unauthorized family
    UNAUTHORIZED_ERROR = 401_00
    
    # refuse family
    REFUSE_ACCESS_ERROR = 403_00
    
    # not found family
    ITEM_NOT_FOUND = 404
    NOT_FOUND_ERROR = 404_00
    
    # duplicated family
    ITEM_ALREADY_EXISTS = 409
    DUPLICATED_ERROR = 409_00
    
    # server error
    SERVER_ERROR = 500_00


def _api_response(code, message, data) -> dict:
    """
    wrap an api response dict obj
    :param code: error code
    :param message: message
    :param data: requested data
    :return: a dictionary object
    """
    return {'code': code, 'message': message, 'data': data}


def failed_api_response(code, error_msg=None) -> dict:
    """
    wrap an failed response dict obj
    :param code: error code, refers to ErrorCode, can be an integer or a str (error name)
    :param error_msg: external error information
    :return: an api response dictionary
    """
    if isinstance(code, str):
        code = ErrorCode[code]
    if isinstance(code, int):
        try:
            code = ErrorCode(code)
        except ValueError:
            # If not in Enum, keep as int but ideally should be in Enum
            pass
            
    code_value = code.value if isinstance(code, ErrorCode) else code
    
    if error_msg is None:
        error_msg = str(code)

    return _api_response(
        code=code_value,
        message=error_msg,
        data=None
    )


def success_api_response(data=None, message='成功') -> dict:
    """
    wrap a success response dict obj
    :param data: requested data
    :return: an api response dictionary
    """
    return _api_response(ErrorCode.SUCCESS.value, message, data)


def response_wrapper(func):
    """
    decorate a given api-function, parse its return value from a dict to a HttpResponse
    :param func: a api-function
    :return: wrapped function
    """

    def _inner(*args, **kwargs):
        _response = func(*args, **kwargs)
        if isinstance(_response, dict):
            # Existing format: {'code': 0, 'message': '...', 'data': ...}
            # We just wrap it in JsonResponse
            return JsonResponse(_response)
        return _response

    return _inner


def parse_data(request: HttpRequest):
    """Parse request body and generate python dict

    Args:
        request (HttpRequest): all http request

    Returns:
        | request body is malformed = None
        | otherwise                 = python dict
    """
    try:
        return json.loads(request.body.decode())
    except json.JSONDecodeError:
        return None
