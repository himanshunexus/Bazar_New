from django.conf import settings


def site_defaults(request):
    return {
        "DEFAULT_LAT": settings.DEFAULT_LAT,
        "DEFAULT_LNG": settings.DEFAULT_LNG,
        "DEFAULT_RADIUS_KM": settings.DEFAULT_RADIUS_KM,
    }
