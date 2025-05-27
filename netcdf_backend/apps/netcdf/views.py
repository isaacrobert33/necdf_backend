from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from netcdf_backend.apps.netcdf.models import FileCache
from netcdf_backend.apps.netcdf.models import NetCDFFile
from netcdf_backend.apps.netcdf.serializers import FileResponseSerializer
from netcdf_backend.apps.netcdf.serializers import NetCDFFileSerializer
from netcdf_backend.apps.netcdf.serializers import PlotRequestSerializer
from netcdf_backend.apps.netcdf.tasks import process_and_cache_netcdf
from netcdf_backend.apps.netcdf.utils import create_plot_from_filter
from netcdf_backend.apps.netcdf.utils import extract_netcdf_metadata
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
    def get(self, request):
        scenario = request.query_params.get("scenario")
        variable = request.query_params.get("variable")
        season = request.query_params.get("season")
        period = request.query_params.get("period")

        if not all([scenario, variable, season, period]):
            return ErrorResponse(
                {"error": "Missing parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                FileResponseSerializer(
                    {"file_url": f"{settings.MEDIA_URL}{cached.file_path}"},
                ).data,
            )
        except FileCache.DoesNotExist:
            # Trigger async task
            file_path = f"netcdf_files/ensmean_{variable}_{scenario}.nc"
            region_bbox = [29, -11.75, 40.5, -1]  # Tanzania
            process_and_cache_netcdf.delay(
                file_path,
                scenario,
                variable,
                season,
                period,
                region_bbox,
            )
            return SuccessResponse(
                {"status": "Processing started, try again later"},
                status=status.HTTP_202_ACCEPTED,
            )


class GeoJSONView(APIView):
    def get(self, request):
        scenario = request.query_params.get("scenario")
        variable = request.query_params.get("variable")
        season = request.query_params.get("season")
        period = request.query_params.get("period")

        if not all([scenario, variable, season, period]):
            return SuccessResponse(
                {"error": "Missing parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                {"file_url": f"{settings.MEDIA_URL}{cached.file_path}"},
            ).data
            return SuccessResponse(data=data)
        except FileCache.DoesNotExist:
            # Trigger async task
            file_path = f"netcdf_files/ensmean_{variable}_{scenario}.nc"
            region_bbox = [29, -11.75, 40.5, -1]
            process_and_cache_netcdf.delay(
                file_path,
                scenario,
                variable,
                season,
                period,
                region_bbox,
            )
            return SuccessResponse(
                {"status": "Processing started, try again later"},
                status=status.HTTP_202_ACCEPTED,
            )
