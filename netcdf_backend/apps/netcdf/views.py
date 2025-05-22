from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from netcdf_backend.apps.netcdf.models import NetCDFFile
from netcdf_backend.apps.netcdf.serializers import (
    NetCDFFileReadSerializer,
    NetCDFFileSerializer,
)
from netcdf_backend.apps.netcdf.utils import extract_netcdf_metadata
from netcdf_backend.core.success_response import SuccessResponse


class NetCDFUploadView(APIView):
    serializer_class = NetCDFFileSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = NetCDFFileReadSerializer(serializer.instance).data
        return SuccessResponse(status=status.HTTP_200_OK, data=data)


class NetCDFMetadata(APIView):
    def get(self, request: Request, uuid: str):
        obj = get_object_or_404(NetCDFFile, uuid=uuid)
        metadata = extract_netcdf_metadata(obj.file.path)
        return SuccessResponse(status=status.HTTP_200_OK, data=metadata)
