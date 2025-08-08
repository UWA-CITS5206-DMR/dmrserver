from rest_framework import serializers

from .models import Patient, BloodPressure, LabTest


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
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return Patient.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.date_of_birth = validated_data.get("date_of_birth", instance.date_of_birth)
        instance.email = validated_data.get("email", instance.email)
        instance.phone_number = validated_data.get("phone_number", instance.phone_number)
        instance.save()
        return instance


class BloodPressureSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())

    class Meta:
        model = BloodPressure
        fields = [
            "id",
            "patient",
            "systolic",
            "diastolic",
            "measurement_date"
        ]
        read_only_fields = ["id", "measurement_date"]

    def create(self, validated_data):
        return BloodPressure.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.systolic = validated_data.get("systolic", instance.systolic)
        instance.diastolic = validated_data.get("diastolic", instance.diastolic)
        instance.save()
        return instance


class LabTestSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())

    class Meta:
        model = LabTest
        fields = [
            "id",
            "patient",
            "test_name",
            "result",
            "test_date"
        ]
        read_only_fields = ["id", "test_date"]

    def create(self, validated_data):
        return LabTest.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.test_name = validated_data.get("test_name", instance.test_name)
        instance.result = validated_data.get("result", instance.result)
        instance.save()
        return instance
