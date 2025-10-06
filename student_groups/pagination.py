from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class ObservationsPagination(PageNumberPagination):
    """
    Custom pagination for ObservationsViewSet that supports multiple observation types.
    
    Standard DRF pagination expects a single queryset, but ObservationsViewSet returns
    a dictionary of multiple observation types. This paginator wraps that structure
    while providing standard pagination metadata (count, next, previous).
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def paginate_observations(self, observations_dict, request, view=None):
        """
        Paginate a dictionary of observation querysets.
        
        Args:
            observations_dict: Dict with keys like 'blood_pressures', 'heart_rates', etc.
            request: The request object
            view: The view instance (optional)
            
        Returns:
            Paginated dictionary of observations
        """
        self.request = request
        
        # Get page size from query params or use default
        page_size = self.get_page_size(request)
        if page_size is None:
            page_size = self.page_size
            
        # Apply page_size limit to each observation type
        paginated_observations = {}
        total_count = 0
        
        for key, queryset in observations_dict.items():
            # Convert queryset to list and apply slicing
            all_items = list(queryset)
            total_count += len(all_items)
            
            # Apply pagination
            paginated_observations[key] = all_items[:page_size]
        
        # Store for get_paginated_response
        self.total_count = total_count
        self.page_size_value = page_size
        
        return paginated_observations
    
    def get_paginated_response(self, data):
        """
        Return paginated response in standard DRF format.
        
        Returns:
            Response with standard pagination structure:
            {
                "count": total_items,
                "next": next_page_url or null,
                "previous": previous_page_url or null,
                "results": {observation_data}
            }
        """
        return Response(OrderedDict([
            ('count', self.total_count),
            ('next', None),  # Currently not supporting page navigation
            ('previous', None),  # Currently not supporting page navigation
            ('results', data)
        ]))
