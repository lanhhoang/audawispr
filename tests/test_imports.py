"""Verify public API imports from audawispr."""

import sys

# All exception classes exposed by the package
EXCEPTION_CLASSES = [
    "AudawisprError",
    "InputAudioError",
    "TranscriptionError",
    "SegmentationError",
    "EnrichmentError",
    "ManifestError",
    "ClippingError",
    "ExportError",
    "CancelledError",
    "OneShotError",
]


def test_imports() -> list[str]:
    errors: list[str] = []

    # Test 1: import __version__
    try:
        from audawispr import __version__

        if not isinstance(__version__, str) or not __version__:
            errors.append("__version__ is not a non-empty string")
        else:
            print(f"  ✓ __version__ = {__version__!r}")
    except Exception as e:
        errors.append(f"Import __version__ failed: {e}")

    # Test 2: import Pipeline
    try:
        from audawispr import Pipeline

        print(f"  ✓ Pipeline = {Pipeline!r}")
    except Exception as e:
        errors.append(f"Import Pipeline failed: {e}")

    # Test 3: import all exception classes
    exception_objects: dict[str, type] = {}
    for name in EXCEPTION_CLASSES:
        try:
            exc = getattr(__import__("audawispr", fromlist=[name]), name)
            exception_objects[name] = exc
            print(f"  ✓ {name} imported")
        except Exception as e:
            errors.append(f"Import {name} failed: {e}")

    # Test 4: verify AudawisprError is the base class of all other exceptions
    if "AudawisprError" in exception_objects:
        audawispr_error = exception_objects["AudawisprError"]
        for name, exc in exception_objects.items():
            if name == "AudawisprError":
                continue
            if not issubclass(exc, audawispr_error):
                errors.append(f"{name} is not a subclass of AudawisprError")
            else:
                print(f"  ✓ {name} inherits from AudawisprError")
    else:
        errors.append("AudawisprError was not imported, cannot verify hierarchy")

    return errors


if __name__ == "__main__":
    errors = test_imports()
    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("\nAll import checks passed.")
    sys.exit(0)
