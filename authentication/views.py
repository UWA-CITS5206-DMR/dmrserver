from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    API endpoint for user login
    Accepts: {"username": "...", "password": "..."}
    Returns: {"user": {...}} or {"error": "..."}
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    if user and user.is_active:
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'role': getattr(user, 'role', 'student'),  # Default to student
                'firstName': user.first_name,
                'lastName': user.last_name,
                'email': user.email,
            }
        })
    
    return Response(
        {'error': 'Invalid credentials'}, 
        status=status.HTTP_401_UNAUTHORIZED
    )

@api_view(['GET'])
def session(request):
    """
    API endpoint to check current user session
    Returns current user info if authenticated
    """
    if request.user.is_authenticated:
        return Response({
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'role': getattr(request.user, 'role', 'student'),
                'firstName': request.user.first_name,
                'lastName': request.user.last_name,
                'email': request.user.email,
            }
        })
    
    return Response(
        {'error': 'Not authenticated'}, 
        status=status.HTTP_401_UNAUTHORIZED
    )

@api_view(['POST'])
def logout(request):
    """
    API endpoint for user logout
    """
    # For session-based auth, you might want to clear session
    # For now, just return success (frontend handles token removal)
    return Response({'message': 'Logged out successfully'})