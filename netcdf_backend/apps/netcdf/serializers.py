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
