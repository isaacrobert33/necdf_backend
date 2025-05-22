from rest_framework import serializers

from netcdf_backend.apps.netcdf.models import NetCDFFile


class NetCDFFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)

    class Meta:
        model = NetCDFFile
        fields = ("file",)


class NetCDFFileReadSerializer(serializers.ModelSerializer[NetCDFFile]):
    file = serializers.FileField(use_url=True)

    class Meta:
        model = NetCDFFile
        fields = (
            "uuid",
            "file",
            "created_at",
        )


class PlotRequestSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    variable = serializers.CharField()
    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)
    filters = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()), required=False
    )
    min_lat = serializers.FloatField(required=False)
    max_lat = serializers.FloatField(required=False)
    min_lon = serializers.FloatField(required=False)
    max_lon = serializers.FloatField(required=False)
