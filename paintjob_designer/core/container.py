# coding: utf-8

from importlib import import_module
from typing import Any, Callable


class Container:
    """
    Resolves services by name. Each service is registered as a factory lambda
    that receives the container, enabling dependency wiring between services.
    Instances are created once on first access and cached.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[["Container"], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register(self, name: str, factory: Callable[["Container"], Any]) -> None:
        """Register a service factory. Factory receives the container for resolving deps."""
        self._factories[name] = factory
        self._instances.pop(name, None)

    def register_lazy(self, name: str, target: str, *deps: str) -> None:
        """Register a service by import path, importing nothing until it is used.

        `target` is "module.path:ClassName" and `deps` are the service names
        passed to it positionally.
        """
        self.register(
            name,
            lambda c: self._load(target)(*(c.resolve(dep) for dep in deps)),
        )

    def resolve(self, name: str) -> Any:
        """Resolve a service by name. Creates on first call, caches thereafter."""
        if name not in self._instances:
            if name not in self._factories:
                raise KeyError(f"No service registered for '{name}'")

            self._instances[name] = self._factories[name](self)

        return self._instances[name]

    def provider(self, name: str) -> Callable[[], Any]:
        """A handle that resolves `name` the first time it is called, for wiring
        up a consumer without building an expensive service yet."""
        if name not in self._factories:
            raise KeyError(f"No service registered for '{name}'")

        return lambda: self.resolve(name)

    def is_instantiated(self, name: str) -> bool:
        return name in self._instances

    def registered_names(self) -> list[str]:
        return list(self._factories)

    def _load(self, target: str) -> Any:
        module_path, _, attribute = target.partition(":")

        if not attribute:
            raise ValueError(f"'{target}' must be written as 'module.path:Name'")

        return getattr(import_module(module_path), attribute)
