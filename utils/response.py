from rest_framework.response import Response
from rest_framework import status

def api_response(code=0, message='成功', data=None, status_code=status.HTTP_200_OK):
    return Response({
        'code': code,
        'message': message,
        'data': data
    }, status=status_code)
