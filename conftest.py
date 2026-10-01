"""Repository-wide pytest configuration: Hypothesis profiles (select with HYPOTHESIS_PROFILE)."""

import os

from hypothesis import HealthCheck, settings

settings.register_profile("dev", max_examples=100)
settings.register_profile(
    "ci", max_examples=500, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
