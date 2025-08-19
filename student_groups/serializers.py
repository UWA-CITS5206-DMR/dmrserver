from rest_framework import serializers

from .models import Note, BloodPressure, HeartRate, BodyTemperature


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = [
            "id",
            "patient",
            "user",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return Note.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.content = validated_data.get("content", instance.content)
        instance.save()
        return instance


class BloodPressureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodPressure
        fields = [
            "id",
            "patient",
            "user",
            "systolic",
            "diastolic",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        return BloodPressure.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.systolic = validated_data.get("systolic", instance.systolic)
        instance.diastolic = validated_data.get("diastolic", instance.diastolic)
        instance.save()
        return instance


class HeartRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeartRate
        fields = [
            "id",
            "patient",
            "user",
            "heart_rate",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        return HeartRate.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.heart_rate = validated_data.get("heart_rate", instance.heart_rate)
        instance.save()
        return instance


class BodyTemperatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyTemperature
        fields = [
            "id",
            "patient",
            "user",
            "temperature",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        return BodyTemperature.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.temperature = validated_data.get("temperature", instance.temperature)
        instance.save()
        return instance
