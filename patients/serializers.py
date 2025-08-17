from rest_framework import serializers

from .models import Patient, File


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "date_of_birth",
            "email",
            "phone_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return Patient.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.date_of_birth = validated_data.get(
            "date_of_birth", instance.date_of_birth
        )
        instance.email = validated_data.get("email", instance.email)
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        instance.save()
        return instance


class FileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        max_length=None,
        use_url=True,  # Set to True to return the file's URL, otherwise return the file name
    )

    class Meta:
        model = File
        fields = ["id", "display_name", "file", "created_at"]
        read_only_fields = ["id", "display_name", "created_at"]

    def create(self, validated_data):
        validated_data["display_name"] = validated_data["file"].name
        return super().create(validated_data)
