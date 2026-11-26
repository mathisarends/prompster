from fastapi_canon import Feature

from backend.features.health.infrastructure import HealthProvider
from backend.features.health.presentation import HEALTH_ERRORS

# The health routes are mounted at the application root rather than under the
# versioned API prefix, so the feature only contributes providers and errors.
feature = Feature(
    name="health",
    providers=[HealthProvider],
    errors=HEALTH_ERRORS,
)
