from polymarq_backend.core.error_response import ErrorResponse
from rest_framework import status

# def client_required(function=None):
#     """
#     Decorator for views that checks that the logged in user is a client,
#     else returns a 403 Forbidden response.
#     """
#     # def wrapper(*args, **kwargs):
#     #     request = args[0]
#     #     if not request.user.is_client:
#     # return Response(
#     #     {"error": "You are not authorized to access this resource"},
#     #     status=status.HTTP_403_FORBIDDEN,
#     # )
#     #     return func(*args, **kwargs)
#     # return wrapper

#     decorator = user_passes_test(
#         lambda user: user.is_client and user.is_active and user.is_verified,  # type: ignore
#     )
#     if function:
#         return decorator(function)
#     return decorator


# def client_required(function=None):
#     """
#     Decorator for views that checks that the logged in user is a technician,
#     else returns a 403 Forbidden response.
#     """

#     user_is_client = user_passes_test(
#         lambda user: user.is_client and user.is_active and user.is_verified,  # type: ignore
#     )

#     def _wrapped_view(request, *args, **kwargs):
#         if user_is_client(request.user):
#             if function:
#                 return function(request, *args, **kwargs)
#         else:
#             return Response(
#                 {"error": "You are not authorized to access this resource"},
#                 status=status.HTTP_403_FORBIDDEN,
#             )

#     if function:
#         return _wrapped_view
#     return user_is_client


def client_required(function=None):
    """
    Decorator for views that checks that the logged in user is a client,
    else returns a 403 Forbidden response.
    """

    user_is_client = lambda user: user.is_client and user.is_active and user.is_verified  # type: ignore # noqa: E731

    def _wrapped_view(self, request, *args, **kwargs):
        if user_is_client(request.user):
            if function:
                return function(self, request, *args, **kwargs)
        else:
            return ErrorResponse(
                details="You are not authorized to access this resource",
                status=status.HTTP_403_FORBIDDEN,
            )

    if function:
        return _wrapped_view

    return user_is_client


def technician_required(function=None):
    """
    Decorator for views that checks that the logged in user is a technician,
    else returns a 403 Forbidden response.
    """

    user_is_technician = (
        lambda user: user.is_technician and user.is_active and user.is_verified
    )  # type: ignore

    def _wrapped_view(self, request, *args, **kwargs):
        if user_is_technician(request.user):
            if function:
                return function(self, request, *args, **kwargs)
        else:
            return ErrorResponse(
                details="You are not authorized to access this resource",
                status=status.HTTP_403_FORBIDDEN,
            )

    if function:
        return _wrapped_view

    return user_is_technician


def client_or_technician_required(function=None):
    """
    Decorator for views that checks that the logged in user is a technician,
    else returns a 403 Forbidden response.
    """

    user_is_client = (
        lambda user: user.is_technician and user.is_active and user.is_verified
    )  # type: ignore
    user_is_technician = (
        lambda user: user.is_client and user.is_active and user.is_verified
    )  # type: ignore

    def _wrapped_view(self, request, *args, **kwargs):
        if user_is_client(request.user) or user_is_technician(request.user):
            if function:
                return function(self, request, *args, **kwargs)
        else:
            return ErrorResponse(
                details="You are not authorized to access this resource",
                status=status.HTTP_403_FORBIDDEN,
            )

    if function:
        return _wrapped_view

    return user_is_client or user_is_technician


def technician_required_and_verified(function=None):
    """
    Decorator for views that checks that the logged in user is a verified technician,
    else returns a 403 Forbidden response.
    """

    user_is_verified_technician = (
        lambda user: user.is_technician
        and user.is_active
        and user.is_verified
        and user.technician_verified
    )  # type: ignore

    def _wrapped_view(self, request, *args, **kwargs):
        if user_is_verified_technician(request.user):
            if function:
                return function(self, request, *args, **kwargs)
        else:
            return ErrorResponse(
                details="You are not authorized to access this resource",
                status=status.HTTP_403_FORBIDDEN,
            )

    if function:
        return _wrapped_view

    return user_is_verified_technician
