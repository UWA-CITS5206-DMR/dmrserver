"""
Caching utilities for the DMR application.

This module provides a comprehensive caching system designed to handle:
1. Query caching with parameter-aware cache keys
2. Automatic cache invalidation on writes
3. Role-based and filter-based cache strategies
4. Consistent cache key generation following best practices

Cache Key Strategy:
- Format: `{app}:{model}:{action}:{param1_value}:{param2_value}`
- Example: `patients:file:list:patient_1:user_1:role_student`
- Includes: application, model name, action, and sorted parameters
"""

import contextlib
import hashlib
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Model
from rest_framework import status
from rest_framework.response import Response


class CacheKeyGenerator:
    """Generate consistent cache keys for API queries."""

    # Maximum TTL for cache (default 5 minutes for frequently polled data)
    DEFAULT_TTL = getattr(settings, "DMR_CACHE_TTL", 300)

    @staticmethod
    def _serialize_params(params: dict[str, "Any"]) -> str:
        """
        Serialize parameters to a consistent string format.

        Ensures same parameters always generate the same key,
        regardless of parameter order.
        """
        # Sort by key for consistency
        sorted_params = sorted(params.items())
        # Use JSON for reliable serialization
        return json.dumps(sorted_params, default=str, sort_keys=True)

    @staticmethod
    def _hash_params(params_str: str) -> str:
        """Hash parameters string for URL-safe key format."""
        # Using SHA256 instead of MD5 for security
        return hashlib.sha256(params_str.encode()).hexdigest()[:16]

    @staticmethod
    def generate_key(  # type: ignore[misc]
        app: str,
        model: str,
        action: str,
        **params: Any,  # type: ignore[misc]
    ) -> str:
        """
        Generate a cache key following best practices.

        Args:
            app: Application name (e.g., 'patients', 'student_groups')
            model: Model name (e.g., 'file', 'patient', 'observation')
            action: Action name (e.g., 'list', 'retrieve', 'filter')
            **params: Query parameters to include in cache key

        Returns:
            Cache key string in format: app:model:action:hash(params)

        Examples:
            >>> CacheKeyGenerator.generate_key(
            ...     'patients', 'file', 'list',
            ...     patient_id=1, user_id=2, category='Imaging'
            ... )
            'patients:file:list:a1b2c3d4e5f6...'
        """
        if not params:
            base_key = f"{app}:{model}:{action}"
        else:
            params_str = CacheKeyGenerator._serialize_params(params)
            params_hash = CacheKeyGenerator._hash_params(params_str)
            base_key = f"{app}:{model}:{action}:{params_hash}"

        return base_key

    @classmethod
    def generate_invalidation_keys(
        cls,
        app: str,
        model: str,
        **params: Any,  # type: ignore[misc]
    ) -> list[str]:
        """
        Generate cache keys to invalidate on write operations.

        When a model is created/updated/deleted, we need to invalidate
        all related query caches. This generates keys for common query
        patterns that might be affected.

        Args:
            app: Application name
            model: Model name
            **params: Parameters that identify the affected scope

        Returns:
            List of cache keys that should be invalidated

        Examples:
            >>> CacheKeyGenerator.generate_invalidation_keys(
            ...     'patients', 'file', patient_id=1, user_id=2
            ... )
            ['patients:file:list:*', 'patients:file:list:patient_1:*', ...]
        """
        keys_to_invalidate = []

        # Always invalidate list caches for the model
        keys_to_invalidate.append(f"{app}:{model}:list:*")

        # Invalidate specific filter caches
        if params:
            # Generate partial keys for common filtering scenarios
            for param_key, param_value in params.items():
                keys_to_invalidate.append(
                    f"{app}:{model}:list:{param_key}_{param_value}:*"
                )

        return keys_to_invalidate


class CacheManager:
    """Manage cache operations for model queries and writes."""

    @staticmethod
    def get_cached(key: str, default: Any = None) -> Any:
        """Get value from cache."""
        return cache.get(key, default)

    @staticmethod
    def set_cached(
        key: str,
        value: Any,
        timeout: int | None = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds (None uses default)
        """
        if timeout is None:
            timeout = CacheKeyGenerator.DEFAULT_TTL
        cache.set(key, value, timeout)

    @staticmethod
    def invalidate_cache(patterns: str | list[str]) -> None:
        """
        Invalidate cache keys matching a pattern or list of patterns.

        For locmem cache, clears all matching keys manually.
        For Redis cache, uses delete_pattern if available.

        Pattern matching logic:
        - `app:model:write:param:*` clears all `app:model:*` cache keys
        - Strips the `:write:*` part to match all read cache keys for that model

        Args:
            patterns: Cache key pattern or list of patterns (e.g., 'patients:file:list:*')
        """
        # Convert single string to list
        pattern_list = [patterns] if isinstance(patterns, str) else patterns

        for pattern in pattern_list:
            # Try redis delete_pattern first
            with contextlib.suppress(AttributeError):
                # This works with django-redis
                cache.delete_pattern(pattern)  # type: ignore[attr-defined]
                return

            # Fallback for locmem: manually clear matching keys
            try:
                # Access the underlying cache dict directly
                # For ConnectionProxy to LocMemCache, _cache is an OrderedDict
                if hasattr(cache, "_cache"):
                    cache_dict = cache._cache  # type: ignore[attr-defined]
                    pattern_stripped = pattern.rstrip("*")

                    # Handle write invalidation patterns
                    # Pattern like "app:model:write:param:*" should clear "app:model:*" cache
                    if ":write:" in pattern_stripped:
                        # Extract app and model from write pattern
                        parts = pattern_stripped.split(":write:")
                        model_prefix = parts[0]  # e.g., "student_groups:observations"
                        # Match all keys that start with this app:model prefix
                        pattern_prefix = model_prefix
                    else:
                        # Regular pattern matching
                        pattern_prefix = pattern_stripped

                    # Find all keys that match the pattern
                    # Keys have format `:VERSION:actual_key`, so we need to extract actual_key
                    keys_to_delete = []
                    for k in cache_dict:
                        # Extract actual key from `:1:actual_key` format
                        if k.startswith(":"):
                            parts = k.split(":", 2)  # Split into ['', 'VERSION', 'actual_key']
                            if len(parts) == 3:
                                actual_key = parts[2]
                            else:
                                actual_key = k
                        else:
                            actual_key = k

                        # Check if pattern matches
                        if pattern_prefix in actual_key:
                            keys_to_delete.append(actual_key)

                    # Delete matching keys using cache.delete() to handle expiry properly
                    for key in keys_to_delete:
                        cache.delete(key)
            except (AttributeError, TypeError):
                pass


def cache_retrieve_response(
    app: str,
    model: str,
    cache_key_params: list[str] | None = None,
    ttl: int | None = None,
) -> Callable:
    """
    Decorator to cache GET/retrieve responses.

    Caches the serialized response data for list/retrieve endpoints.

    Args:
        app: Application name
        model: Model name
        cache_key_params: List of query parameter names to include in cache key
                         (e.g., ['patient', 'user', 'category'])
        ttl: Cache timeout in seconds

    Usage:
        @cache_retrieve_response('patients', 'file', ['patient_id', 'category'])
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)

    Example:
        When requesting GET /patients/1/files/?category=Imaging
        Cache key will be: patients:file:list:hash({category: Imaging, patient_id: 1})
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
            # Only cache GET requests
            if request.method != "GET":
                return func(self, request, *args, **kwargs)

            # Build cache key parameters from query params and URL kwargs
            cache_params = {}

            if cache_key_params:
                for param in cache_key_params:
                    # Check query parameters first
                    value = request.query_params.get(param)
                    # Then check URL kwargs
                    if value is None and param in kwargs:
                        value = kwargs[param]

                    if value is not None:
                        cache_params[param] = value

            # Add pagination info to cache key
            page = request.query_params.get("page", "1")
            cache_params["page"] = page

            # Generate cache key
            action = getattr(self, "action", "list")
            cache_key = CacheKeyGenerator.generate_key(
                app,
                model,
                action,
                **cache_params,
            )

            # Try to get from cache
            cached_response = CacheManager.get_cached(cache_key)
            if cached_response is not None:
                # Return cached response data
                return cached_response

            # Call original function
            response = func(self, request, *args, **kwargs)

            # Cache the response (only success responses)
            if response.status_code == status.HTTP_200_OK:
                CacheManager.set_cached(cache_key, response.data, ttl)

            return response

        return wrapper

    return decorator


def invalidate_cache_on_write(
    app: str,
    model: str,
    invalidate_params: list[str] | None = None,
) -> Callable:
    """
    Decorator to invalidate related caches on write operations.

    When create/update/delete operations succeed, invalidate all related
    query caches that might be affected.

    Args:
        app: Application name
        model: Model name
        invalidate_params: List of model field names to use for cache invalidation
                          (e.g., ['patient_id', 'user_id'])

    Usage:
        @invalidate_cache_on_write('patients', 'file', ['patient_id', 'user_id'])
        def perform_create(self, serializer):
            super().perform_create(serializer)

    Example:
        When creating a file with patient_id=1, user_id=2:
        Invalidates: patients:file:list:*, patients:file:list:patient_id_1:*, etc.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Call original function
            result = func(self, *args, **kwargs)

            # Extract instance being modified
            instance = None
            if args and isinstance(args[0], Model):
                instance = args[0]
            elif hasattr(self, "instance") and self.instance:
                instance = self.instance

            if instance and invalidate_params:
                # Build invalidation parameters from instance
                invalidation_data = {}
                for param in invalidate_params:
                    value = getattr(instance, param, None)
                    if value is not None:
                        invalidation_data[param] = value

                # Generate and invalidate cache keys
                keys_to_invalidate = (
                    CacheKeyGenerator.generate_invalidation_keys(
                        app,
                        model,
                        **invalidation_data,
                    )
                )

                for key_pattern in keys_to_invalidate:
                    CacheManager.invalidate_cache(key_pattern)

            return result

        return wrapper

    return decorator


class CacheMixin:
    """
    Mixin for ViewSets to add caching capabilities.

    Usage:
        class FileViewSet(CacheMixin, viewsets.ModelViewSet):
            cache_app = 'patients'
            cache_model = 'file'
            cache_retrieve_params = ['patient_id', 'category']
            cache_invalidate_params = ['patient_id', 'user_id']
            cache_ttl = 300
    """

    cache_app: str = "app"
    cache_model: str = "model"
    cache_retrieve_params: list[str] = []
    cache_invalidate_params: list[str] = []
    cache_ttl: int | None = None

    def list(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """Override list to add caching."""
        # Only cache GET requests
        if request.method != "GET":
            return super().list(request, *args, **kwargs)

        # Build cache key
        cache_params = {}
        for param in self.cache_retrieve_params:
            value = request.query_params.get(param)
            if value is None and param in kwargs:
                value = kwargs[param]
            if value is not None:
                cache_params[param] = value

        page = request.query_params.get("page", "1")
        cache_params["page"] = page

        cache_key = CacheKeyGenerator.generate_key(
            self.cache_app,
            self.cache_model,
            "list",
            **cache_params,
        )

        # Try cache
        cached_data = CacheManager.get_cached(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        # Call parent
        response = super().list(request, *args, **kwargs)

        # Cache if successful
        if response.status_code == status.HTTP_200_OK:
            CacheManager.set_cached(cache_key, response.data, self.cache_ttl)

        return response

    def perform_create(self, serializer: Any) -> None:
        """Override to invalidate cache on create."""
        super().perform_create(serializer)

        instance = serializer.instance
        if instance and self.cache_invalidate_params:
            invalidation_data = {}
            for param in self.cache_invalidate_params:
                value = getattr(instance, param, None)
                if value is not None:
                    invalidation_data[param] = value

            keys_to_invalidate = (
                CacheKeyGenerator.generate_invalidation_keys(
                    self.cache_app,
                    self.cache_model,
                    **invalidation_data,
                )
            )

            for key_pattern in keys_to_invalidate:
                CacheManager.invalidate_cache(key_pattern)

    def perform_update(self, serializer: Any) -> None:
        """Override to invalidate cache on update."""
        super().perform_update(serializer)

        instance = serializer.instance
        if instance and self.cache_invalidate_params:
            invalidation_data = {}
            for param in self.cache_invalidate_params:
                value = getattr(instance, param, None)
                if value is not None:
                    invalidation_data[param] = value

            keys_to_invalidate = (
                CacheKeyGenerator.generate_invalidation_keys(
                    self.cache_app,
                    self.cache_model,
                    **invalidation_data,
                )
            )

            for key_pattern in keys_to_invalidate:
                CacheManager.invalidate_cache(key_pattern)

    def perform_destroy(self, instance: Any) -> None:
        """Override to invalidate cache on delete."""
        if instance and self.cache_invalidate_params:
            invalidation_data = {}
            for param in self.cache_invalidate_params:
                value = getattr(instance, param, None)
                if value is not None:
                    invalidation_data[param] = value

            keys_to_invalidate = (
                CacheKeyGenerator.generate_invalidation_keys(
                    self.cache_app,
                    self.cache_model,
                    **invalidation_data,
                )
            )

        super().perform_destroy(instance)

        if instance and self.cache_invalidate_params:
            for key_pattern in keys_to_invalidate:
                CacheManager.invalidate_cache(key_pattern)
