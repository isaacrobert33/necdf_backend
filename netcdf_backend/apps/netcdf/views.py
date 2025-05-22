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
    PlotRequestSerializer,
)
from netcdf_backend.apps.netcdf.utils import (
    create_plot_from_filter,
    extract_netcdf_metadata,
)
from netcdf_backend.core.error_response import ErrorResponse
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
        instance = serializer.instance
        metadata = extract_netcdf_metadata(instance.file.path)
        metadata["uuid"] = instance.uuid
        metadata["created_at"] = instance.created_at
        print(metadata)
        return SuccessResponse(status=status.HTTP_200_OK, data=metadata)


class NetCDFMetadata(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request, uuid: str):
        obj = get_object_or_404(NetCDFFile, uuid=uuid)
        metadata = extract_netcdf_metadata(obj.file.path)
        metadata["uuid"] = uuid
        metadata["created_at"] = obj.created_at
        return SuccessResponse(status=status.HTTP_200_OK, data=metadata)


class NCDataPlot(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request, uuid: str):
        serializer = PlotRequestSerializer(data=request.data)
        response = create_plot_from_filter(serializer=serializer)
        return (
            SuccessResponse(status=status.HTTP_200_OK, data=response[0])
            if response[1] == "success"
            else ErrorResponse(
                status=status.HTTP_400_BAD_REQUEST, message=response[0]["error"]
            )
        )
