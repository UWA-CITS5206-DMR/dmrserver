import mimetypes
import io
from wsgiref.util import FileWrapper
from django.http import Http404, HttpResponse, HttpResponseForbidden
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from PyPDF2 import PdfReader, PdfWriter

from core.permissions import (
    PatientPermission,
    FileAccessPermission,
    FileManagementPermission,
)
from .models import Patient, File
from .serializers import PatientSerializer, FileSerializer


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [PatientPermission]

    @action(detail=True, methods=["post"], serializer_class=FileSerializer)
    def upload_file(self, request, pk=None):
        patient = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            patient=patient, display_name=serializer.validated_data["file"].name
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [FileManagementPermission]

    def get_queryset(self):
        return File.objects.filter(patient_id=self.kwargs["patient_pk"])

    @extend_schema(
        summary="View a specific file",
        description="Allows users with permission to view a file's content. For paginated PDFs, a 'page' or 'range' query parameter can be used.",
    )
    @action(detail=True, methods=["get"], permission_classes=[FileAccessPermission])
    def view(self, request, pk=None, patient_pk=None):
        file_instance = self.get_object()

        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        page_query = request.query_params.get("page")
        range_query = request.query_params.get("range")

        if file_instance.requires_pagination:
            return self._serve_paginated_pdf(
                file_instance, request.user, page_query, range_query
            )

        # For non-paginated files, serve the whole file
        return self._serve_whole_file(file_instance)

    def _get_authorized_page_range(self, file_instance, user):
        """Get the authorized page range for a user from approved lab requests"""
        from student_groups.models import ApprovedFile

        if user.is_staff:
            return None  # Staff can access all pages

        approved_file = ApprovedFile.objects.filter(
            file=file_instance, lab_request__user=user, lab_request__status="completed"
        ).first()

        return approved_file.page_range if approved_file else None

    def _parse_page_range(self, range_str):
        """Parse page range string like '1-5' or '7' into a list of page numbers"""
        if not range_str:
            return []

        pages = []
        for part in range_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = map(int, part.split("-"))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))
        return pages

    def _serve_paginated_pdf(self, file_instance, user, page_query, range_query):
        """Serve specific pages of a PDF file based on authorization"""
        try:
            authorized_range = self._get_authorized_page_range(file_instance, user)

            if not authorized_range and not user.is_staff:
                return HttpResponseForbidden(
                    "No authorized page range found for this file."
                )

            # Determine which pages to extract
            if page_query:
                requested_pages = [int(page_query)]
            elif range_query:
                requested_pages = self._parse_page_range(range_query)
            elif authorized_range:
                requested_pages = self._parse_page_range(authorized_range)
            else:
                return HttpResponseForbidden("No page range specified.")

            # For non-staff users, verify requested pages are within authorized range
            if not user.is_staff and authorized_range:
                authorized_pages = self._parse_page_range(authorized_range)
                if not all(page in authorized_pages for page in requested_pages):
                    return HttpResponseForbidden("Requested pages are not authorized.")

            # Extract pages from PDF
            with file_instance.file.open("rb") as pdf_file:
                reader = PdfReader(pdf_file)
                writer = PdfWriter()

                total_pages = len(reader.pages)

                for page_num in requested_pages:
                    if 1 <= page_num <= total_pages:
                        writer.add_page(
                            reader.pages[page_num - 1]
                        )  # Convert to 0-based index

                if len(writer.pages) == 0:
                    return HttpResponseForbidden(
                        "No valid pages found in the requested range."
                    )

                # Create response with extracted pages
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                output_buffer.seek(0)

                response = HttpResponse(
                    output_buffer.getvalue(), content_type="application/pdf"
                )
                filename = f"{file_instance.display_name}_pages_{'-'.join(map(str, requested_pages))}.pdf"
                response["Content-Disposition"] = f'inline; filename="{filename}"'
                return response

        except Exception as e:
            return HttpResponseForbidden(f"Error processing PDF: {str(e)}")

    def _serve_whole_file(self, file_instance):
        """Serve the entire file content"""
        try:
            wrapper = FileWrapper(file_instance.file.open("rb"))
            content_type = mimetypes.guess_type(file_instance.file.name)[0]
            response = HttpResponse(wrapper, content_type=content_type)
            response["Content-Disposition"] = (
                f"inline; filename={file_instance.display_name}"
            )
            return response
        except FileNotFoundError:
            raise Http404("File not found")
