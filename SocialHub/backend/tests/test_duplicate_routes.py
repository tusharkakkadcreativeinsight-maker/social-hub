import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

def _get_route_method_path_pairs():
    """Extract (method, path) pairs from all routes.
    
    FastAPI routes can be:
    - Route objects: have .methods and .path
    - _IncludedRouter objects: have .routes but no .path directly (nested routers)
    - WebSocket routes: have .path but sometimes no .methods
    """
    pairs = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            # Standard API route
            for method in route.methods or []:
                if method not in {'HEAD', 'OPTIONS'}:
                    pairs.append((method, route.path))
        elif hasattr(route, 'routes'):
            # Included router - recurse into its routes
            for sub_route in route.routes:
                if hasattr(sub_route, 'methods') and hasattr(sub_route, 'path'):
                    for method in sub_route.methods or []:
                        if method not in {'HEAD', 'OPTIONS'}:
                            pairs.append((method, sub_route.path))
    return pairs

def test_no_duplicate_method_path_routes():
    pairs = _get_route_method_path_pairs()
    duplicates = [f"{m} {p} x{c}" for (m,p), c in Counter(pairs).items() if c > 1]
    assert not duplicates, 'Duplicate route registrations found: ' + ', '.join(duplicates)