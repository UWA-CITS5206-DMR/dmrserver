# DMR Project Development Guide

## Project Overview

The Digital Medical Records (DMR) system is a Django REST API backend designed for medical record simulation and
management. The system provides:

- **Patient Management**: Complete patient information and file management
- **Medical Observations**: Recording of vital signs (blood pressure, heart rate, body temperature)
- **Student Groups**: Medical student grouping and management functionality
- **REST API**: Full RESTful API with automatic documentation
- **Admin Interface**: Django admin panel for system management

## Code style/formatting

This project uses `ruff` for linting and formatting. To check your code, run:

```bash
uv run ruff check .
```

## Database Setup and Management

### Working with Migrations

#### Creating New Migrations

```bash
# When you modify models, create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate
```

#### Migration Best Practices

1. **Always create migrations for model changes**
2. **Review migration files before applying**
3. **Use descriptive migration names when needed**

```bash
uv run python manage.py makemigrations --name add_patient_phone_field patients
```

## API Development

### Adding New Models

#### Step 1: Define the Model

```python
# Example: patients/models.py
class MedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    condition = models.CharField(max_length=200)
    diagnosed_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Medical History"
        verbose_name_plural = "Medical Histories"
        ordering = ['-diagnosed_date']

    def __str__(self):
        return f"{self.patient} - {self.condition}"
```

#### Step 2: Create and Apply Migration

```bash
uv run python manage.py makemigrations patients
uv run python manage.py migrate
```

#### Step 3: Create Serializer

```python
# patients/serializers.py
class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = '__all__'
        read_only_fields = ('created_at',)

    def validate_diagnosed_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError(
                "Diagnosed date cannot be in the future."
            )
        return value
```

#### Step 4: Create ViewSet

```python
# patients/views.py
class MedicalHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MedicalHistory.objects.filter(
            patient_id=self.kwargs['patient_pk']
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs['patient_pk'])
```

#### Step 5: Add to URLs

```python
# patients/urls.py
medical_history_router = routers.NestedSimpleRouter(
    router, r'patients', lookup='patient'
)
medical_history_router.register(
    r'medical-history', MedicalHistoryViewSet, basename='medical-history'
)

urlpatterns = router.urls + files_router.urls + medical_history_router.urls
```

## Troubleshooting

### Common Issues

1. **Python version mismatch**: Ensure you have Python 3.12+ installed
2. **uv not found**: Make sure uv is installed and in your PATH
3. **Dependencies not syncing**: Try `uv sync --reinstall` to force reinstall