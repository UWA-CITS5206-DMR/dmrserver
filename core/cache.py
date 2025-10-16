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
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
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
    """Configuration for building cache parameters."""

    cache_key_params: list[str] | None = None
    kwargs: dict | None = None
    user_sensitive: bool = False
    include_page: bool = True
    exclude_params: set[str] | None = None


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
    def generate_key(  # type: ignore[misc]
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
    """Helper class to build cache parameters from request and kwargs."""

    @staticmethod
    def build_from_request(
        request: Request,
        config: CacheParamConfig | None = None,
    ) -> dict[str, object]:
        """Build cache parameters from request query params and kwargs."""
        config = config or CacheParamConfig()
        params = {}
        kwargs = config.kwargs or {}

        # Include configured parameters
        for param in config.cache_key_params or []:
            value = request.query_params.get(param)
            if value is None and param in kwargs:
                value = kwargs[param]  # type: ignore[assignment]
            if value is not None:
                params[param] = value

        # Include pagination if requested and user ID if sensitive
        if config.include_page or config.user_sensitive:
            page = request.query_params.get("page", "1")
            params["page"] = page
            if config.user_sensitive:
                params["user_id"] = request.user.id

        return params

    @staticmethod
    def build_with_all_query_params(
        request: Request,
        *,
        user_sensitive: bool = False,
        exclude_params: set[str] | None = None,
    ) -> dict[str, object]:
        """Build cache parameters including all query params except excluded ones."""
        exclude_params = exclude_params or {"page", "page_size", "format", "callback"}
        params = {
            param: value
            for param, value in request.query_params.items()
            if param not in exclude_params
        }

        page = request.query_params.get("page", "1")
        params["page"] = page
        if user_sensitive:
            params["user_id"] = request.user.id

        return params


def cache_retrieve_response(
    app: str,
    model: str,
    cache_key_params: list[str] | None = None,
    ttl: int | None = None,
    *,
    user_sensitive: bool = False,
) -> Callable:
    """Decorator to cache GET/retrieve responses based on query parameters."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(
            self: object, request: Request, *args: object, **kwargs: object
        ) -> object:
            if request.method != "GET":
                return func(self, request, *args, **kwargs)

            config = CacheParamConfig(
                cache_key_params=cache_key_params,
                kwargs=kwargs,
                user_sensitive=user_sensitive,
            )
            params = CacheParamBuilder.build_from_request(request, config)

            action = getattr(self, "action", "list")
            cache_key = CacheKeyGenerator.generate_key(app, model, action, **params)

            cached_response = CacheManager.get_cached(cache_key)
            if cached_response is not None:
                return cached_response

            response = func(self, request, *args, **kwargs)

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
    """Decorator to invalidate related caches on write operations (create/update/delete)."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self: object, *args: object, **kwargs: object) -> object:
            result = func(self, *args, **kwargs)

            instance = None
            if args and isinstance(args[0], Model):
                instance = args[0]
            elif hasattr(self, "instance") and self.instance:
                instance = self.instance

            if instance and invalidate_params:
                invalidation_data = {}
                for param in invalidate_params:
                    value = getattr(instance, param, None)
                    if value is not None:
                        invalidation_data[param] = value

                if invalidation_data:
                    keys_to_invalidate = CacheKeyGenerator.generate_invalidation_keys(
                        app,
                        model,
                        **invalidation_data,
                    )
                    for key_pattern in keys_to_invalidate:
                        CacheManager.invalidate_cache(key_pattern)

            return result

        return wrapper

    return decorator


class CacheMixin:
    """Mixin for ViewSets to add automatic caching to list and write operations."""

    cache_app: str = "app"
    cache_model: str = "model"
    cache_retrieve_params: ClassVar[list[str]] = []
    cache_invalidate_params: ClassVar[list[str]] = []
    cache_user_sensitive: ClassVar[bool] = False
    cache_ttl: int | None = None

    def _invalidate_cache_for_instance(self, instance: Model | None) -> None:
        """Extract parameters from instance and invalidate related caches."""
        if not instance or not self.cache_invalidate_params:
            return

        invalidation_data = {}
        for param in self.cache_invalidate_params:
            value = getattr(instance, param, None)
            if value is not None:
                invalidation_data[param] = value

        if invalidation_data:
            keys_to_invalidate = CacheKeyGenerator.generate_invalidation_keys(
                self.cache_app,
                self.cache_model,
                **invalidation_data,
            )
            for key_pattern in keys_to_invalidate:
                CacheManager.invalidate_cache(key_pattern)

    def list(self, request: Request, *args: object, **kwargs: object) -> object:
        """Override list to add caching."""
        if request.method != "GET":
            return super().list(request, *args, **kwargs)

        params = CacheParamBuilder.build_with_all_query_params(
            request,
            user_sensitive=self.cache_user_sensitive,
        )

        # Add any configured retrieve params not already captured
        for param in self.cache_retrieve_params:
            if param not in params:
                value = request.query_params.get(param)
                if value is None and hasattr(self, "kwargs") and param in self.kwargs:
                    value = self.kwargs[param]  # type: ignore[attr-defined]
                if value is not None:
                    params[param] = value

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
