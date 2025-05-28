from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from netcdf_backend.apps.netcdf.models import FileCache, NetCDFFile
from netcdf_backend.apps.netcdf.serializers import (
    FileResponseSerializer,
    FilterParameterSerializer,
    NetCDFFileSerializer,
    PlotRequestSerializer,
)
from netcdf_backend.apps.netcdf.tasks import process_and_cache_netcdf
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
                status=status.HTTP_400_BAD_REQUEST,
                message=response[0]["error"],
            )
        )


class GeoTIFFView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        serializer = FilterParameterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scenario = data["scenario"]
        season = data["season"]
        period = data["period"]
        variable = data["variable"]
        variable = variable + "max" if variable == "tas" else data["variable"]

        # Check cache
        try:
            cached = FileCache.objects.get(
                file_type="geotiff",
                scenario=scenario,
                variable=variable,
                season=season,
                period=period,
            )
            return SuccessResponse(
                status=status.HTTP_200_OK,
                data=FileResponseSerializer(
                    cached,
                ).data,
            )
        except FileCache.DoesNotExist:
            # Trigger async task
            file = f"netcdf_backend/data/annual/{variable}_day_Ensmean_{scenario}_r1i1p1f1_gr_merged.nc"  # noqa: E501
            region_bbox = [29, -11.75, 40.5, -1]  # Tanzania
            print("Processing....")
            process_and_cache_netcdf.delay(
                file,
                scenario=scenario,
                variable=variable,
                season=season,
                period=period,
                region_bbox=region_bbox,
            )
            return SuccessResponse(
                status=status.HTTP_202_ACCEPTED,
                data={"status": "Processing started, try again later"},
            )


class GeoJSONView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request):
        serializer = FilterParameterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scenario = data["scenario"]
        season = data["season"]
        period = data["period"]
        variable = data["variable"]
        variable = variable + "max" if variable == "tas" else data["variable"]

        # Check cache
        try:
            cached = FileCache.objects.get(
                file_type="geojson",
                scenario=scenario,
                variable=variable,
                season=season,
                period=period,
            )
            data = FileResponseSerializer(
                cached,
            ).data
            return SuccessResponse(status=status.HTTP_200_OK, data=data)
        except FileCache.DoesNotExist:
            # Trigger async task
            file = f"netcdf_backend/data/annual/{variable}_day_Ensmean_{scenario}_r1i1p1f1_gr_merged.nc"  # noqa: E501
            region_bbox = [29, -11.75, 40.5, -1]
            process_and_cache_netcdf.delay(
                file,
                scenario=scenario,
                variable=variable,
                season=season,
                period=period,
                region_bbox=region_bbox,
            )
            return SuccessResponse(
                status=status.HTTP_202_ACCEPTED,
                data={"status": "Processing started, try again later"},
            )
