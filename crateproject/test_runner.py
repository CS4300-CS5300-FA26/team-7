"""Run tests without requiring a production collectstatic manifest."""
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class StaticFilesTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        self._static_override = override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            }
        )
        self._static_override.enable()
        try:
            return super().setup_test_environment(**kwargs)
        except Exception:
            self._static_override.disable()
            raise

    def teardown_test_environment(self, **kwargs):
        try:
            return super().teardown_test_environment(**kwargs)
        finally:
            self._static_override.disable()
