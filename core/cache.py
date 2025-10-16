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

import hashlib
import json
from dataclasses import dataclass
from typing import ClassVar

from django.conf import settings
from django.core.cache import cache
from django.db.models import Model
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

VERSION_PARTS_COUNT = 3


@dataclass
class CacheParamConfig:
    """
    Configuration for building cache parameters.

    Attributes:
        cache_key_params: Specific query params to include (empty list = include all)
        kwargs: Additional kwargs from URL patterns (e.g., patient_pk)
        user_sensitive: Whether to include user_id in cache keys
    """

    cache_key_params: list[str] | None = None
    kwargs: dict | None = None
    user_sensitive: bool = False


class CacheKeyGenerator:
    """Generate consistent cache keys for API queries."""

    # Maximum TTL for cache (default 5 minutes for frequently polled data)
    DEFAULT_TTL = getattr(settings, "DMR_CACHE_TTL", 300)

    @staticmethod
    def _serialize_params(params: dict[str, object]) -> str:
        """Serialize parameters to a consistent string format."""
        sorted_params = sorted(params.items())
        return json.dumps(sorted_params, default=str, sort_keys=True)

    @staticmethod
    def _hash_params(params_str: str) -> str:
        """Hash parameters string for URL-safe key format."""
        return hashlib.sha256(params_str.encode()).hexdigest()[:16]

    @staticmethod
    def generate_key(
        app: str,
        model: str,
        action: str,
        **params: object,
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
        **params: object,
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
    def get_cached(key: str, default: object = None) -> object:
        """Get value from cache."""
        return cache.get(key, default)

    @staticmethod
    def set_cached(
        key: str,
        value: object,
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
    def _extract_actual_cache_key(cache_key: str) -> str:
        """Extract actual cache key from internal Django cache format."""
        if cache_key.startswith(":"):
            parts = cache_key.split(":", 2)
            return parts[2] if len(parts) == VERSION_PARTS_COUNT else cache_key
        return cache_key

    @staticmethod
    def _extract_pattern_prefix(pattern: str) -> str:
        """Extract the pattern prefix for matching cache keys."""
        pattern_stripped = pattern.rstrip("*")
        if ":write:" in pattern_stripped:
            parts = pattern_stripped.split(":write:")
            return parts[0]
        return pattern_stripped

    @staticmethod
    def _invalidate_redis_cache(patterns: list[str]) -> bool:
        """Attempt to invalidate cache using Redis delete_pattern."""
        try:
            for pattern in patterns:
                cache.delete_pattern(pattern)
        except AttributeError:
            return False
        else:
            return True

    @staticmethod
    def _invalidate_locmem_cache(patterns: list[str]) -> None:
        """Invalidate cache for LocMemCache backend."""
        try:
            if not hasattr(cache, "_cache"):
                return
            cache_dict = cache._cache  # noqa: SLF001
            for pattern in patterns:
                pattern_prefix = CacheManager._extract_pattern_prefix(pattern)
                keys_to_delete = []
                for k in cache_dict:
                    actual_key = CacheManager._extract_actual_cache_key(k)
                    if pattern_prefix in actual_key:
                        keys_to_delete.append(actual_key)
                for key in keys_to_delete:
                    cache.delete(key)
        except (AttributeError, TypeError):
            pass

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

        # Try Redis first, then fallback to LocMemCache
        if not CacheManager._invalidate_redis_cache(pattern_list):
            CacheManager._invalidate_locmem_cache(pattern_list)


class CacheParamBuilder:
    """
    Helper class to build cache parameters from request and kwargs.

    This builder extracts relevant parameters from requests to create
    consistent cache keys. It supports both explicit parameter lists
    and automatic inclusion of all query parameters.
    """

    # Parameters that should never be included in cache keys
    # (they don't affect data content, only presentation)
    NEVER_CACHE_PARAMS: ClassVar[set[str]] = {"format", "callback"}

    @staticmethod
    def build_from_request(
        request: Request,
        config: CacheParamConfig | None = None,
    ) -> dict[str, object]:
        """
        Build cache parameters from request query params and kwargs.

        Two modes:
        1. Explicit: Only include specified cache_key_params (+ page + user_id)
        2. Implicit: Include ALL query params (+ kwargs + page + user_id)

        Args:
            request: The request object containing query parameters
            config: Configuration for parameter extraction

        Returns:
            Dictionary of parameters to include in cache key
        """
        config = config or CacheParamConfig()
        params: dict[str, object] = {}
        kwargs = config.kwargs or {}

        # Mode 1: Explicit cache key params specified
        if config.cache_key_params:
            for param in config.cache_key_params:
                value = request.query_params.get(param)
                if value is None and param in kwargs:
                    value = kwargs[param]
                if value is not None:
                    params[param] = value
        # Mode 2: Include all query params (except never-cache params)
        else:
            # Add all query params except those that never affect cache
            params = {
                param: value
                for param, value in request.query_params.items()
                if param not in CacheParamBuilder.NEVER_CACHE_PARAMS and param != "page"
            }

            # Add URL kwargs (e.g., patient_pk from /patients/{patient_pk}/files/)
            for key, value in kwargs.items():
                if (
                    key not in params
                    and key not in CacheParamBuilder.NEVER_CACHE_PARAMS
                ):
                    params[key] = value

        # Always include page parameter for pagination
        page = request.query_params.get("page", "1")
        params["page"] = page

        # Add user ID for user-sensitive caching
        if config.user_sensitive:
            params["user_id"] = request.user.id

        return params

    @staticmethod
    def extract_invalidation_params(
        instance: Model,
        param_names: list[str],
    ) -> dict[str, object]:
        """
        Extract invalidation parameters from a model instance.

        Args:
            instance: Model instance to extract parameters from
            param_names: List of parameter names to extract

        Returns:
            Dictionary of parameter name to value mappings
        """
        params = {}
        for param in param_names:
            value = getattr(instance, param, None)
            if value is not None:
                params[param] = value
        return params


class CacheMixin:
    """
    Mixin for ViewSets to add automatic caching to list and write operations.

    This mixin provides:
    - Automatic response caching for list operations
    - Automatic cache invalidation on create/update/delete operations
    - Consistent parameter handling using CacheParamConfig
    - User-sensitive caching support

    Configuration attributes:
    - cache_app: Application name for cache keys (e.g., 'patients', 'student_groups')
    - cache_model: Model name for cache keys (e.g., 'files', 'observations')
    - cache_key_params: List of query params to include (empty = include all)
        * Use empty list [] to include ALL query parameters automatically
        * Use specific list ['patient', 'category'] to only include those params
    - cache_invalidate_params: List of MODEL FIELD NAMES for cache invalidation
        * Must be actual model instance attributes (e.g., 'patient_id', 'id')
        * NOT query parameter names - these are extracted from the instance
    - cache_user_sensitive: Whether to include user_id in cache keys
        * True: Different users get different cache entries (for permission-based filtering)
        * False: All users share the same cache (for public data)
    - cache_ttl: Cache timeout in seconds (None uses default TTL from settings)
    """

    cache_app: str = "app"
    cache_model: str = "model"
    cache_key_params: ClassVar[list[str]] = []
    cache_invalidate_params: ClassVar[list[str]] = []
    cache_user_sensitive: ClassVar[bool] = False
    cache_ttl: int | None = None

    def _get_cache_config(self, **kwargs: object) -> CacheParamConfig:
        return CacheParamConfig(
            cache_key_params=self.cache_key_params,
            kwargs=kwargs,
            user_sensitive=self.cache_user_sensitive,
        )

    def _invalidate_cache_for_instance(self, instance: Model | None) -> None:
        """
        Extract parameters from instance and invalidate related caches.

        Uses CacheParamBuilder.extract_invalidation_params for consistent
        parameter extraction logic.

        Args:
            instance: Model instance to extract invalidation params from
        """
        if not instance or not self.cache_invalidate_params:
            return

        # Use centralized parameter extraction
        invalidation_data = CacheParamBuilder.extract_invalidation_params(
            instance,
            self.cache_invalidate_params,
        )

        if invalidation_data:
            keys_to_invalidate = CacheKeyGenerator.generate_invalidation_keys(
                self.cache_app,
                self.cache_model,
                **invalidation_data,
            )
            for key_pattern in keys_to_invalidate:
                CacheManager.invalidate_cache(key_pattern)

    def list(self, request: Request, *args: object, **kwargs: object) -> object:
        """
        Override list to add caching.

        Caches successful GET requests and returns cached data if available.
        Uses centralized CacheParamBuilder for consistent parameter handling.
        """
        if request.method != "GET":
            return super().list(request, *args, **kwargs)

        # Build cache config using centralized configuration
        config = self._get_cache_config(**kwargs)
        params = CacheParamBuilder.build_from_request(request, config)

        cache_key = CacheKeyGenerator.generate_key(
            self.cache_app,
            self.cache_model,
            "list",
            **params,
        )

        # Try cache first
        cached_data = CacheManager.get_cached(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        response = super().list(request, *args, **kwargs)

        # Cache successful response
        if response.status_code == status.HTTP_200_OK:
            CacheManager.set_cached(cache_key, response.data, self.cache_ttl)

        return response

    def perform_create(self, serializer: Serializer) -> None:
        """Override to invalidate cache on create."""
        super().perform_create(serializer)
        self._invalidate_cache_for_instance(serializer.instance)

    def perform_update(self, serializer: Serializer) -> None:
        """Override to invalidate cache on update."""
        super().perform_update(serializer)
        self._invalidate_cache_for_instance(serializer.instance)

    def perform_destroy(self, instance: Model) -> None:
        """Override to invalidate cache on delete."""
        self._invalidate_cache_for_instance(instance)
        super().perform_destroy(instance)
