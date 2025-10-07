from enum import Enum


class Role(Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class ViewContext(Enum):
    STUDENT_READ = "student_read"
    STUDENT_CREATE = "student_create"
    INSTRUCTOR_READ = "instructor_read"
    INSTRUCTOR_WRITE = "instructor_write"
