# coding: utf-8


class Probe:
    """A service whose module the lazy-registration tests watch for being imported."""

    def __init__(self, *parts) -> None:
        self.parts = parts
