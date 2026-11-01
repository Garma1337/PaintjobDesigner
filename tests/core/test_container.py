# coding: utf-8

import sys

import pytest

from paintjob_designer.core.container import Container


class TestRegister:

    def test_register_adds_factory(self):
        container = Container()
        container.register("svc", lambda c: object())

        assert container.resolve("svc") is not None

    def test_register_replaces_existing(self):
        container = Container()
        container.register("svc", lambda c: "first")
        container.resolve("svc")

        container.register("svc", lambda c: "second")

        assert container.resolve("svc") == "second"


class TestResolve:

    def test_resolves_registered_service(self):
        container = Container()
        container.register("svc", lambda c: "value")

        assert container.resolve("svc") == "value"

    def test_caches_instance_on_first_resolve(self):
        container = Container()
        container.register("svc", lambda c: object())

        first = container.resolve("svc")
        second = container.resolve("svc")

        assert first is second

    def test_raises_for_unknown_service(self):
        container = Container()

        with pytest.raises(KeyError, match="No service registered for 'missing'"):
            container.resolve("missing")

    def test_resolves_dependencies_via_container(self):
        container = Container()
        container.register("dep", lambda c: "dep-value")
        container.register("svc", lambda c: {"dep": c.resolve("dep")})

        assert container.resolve("svc") == {"dep": "dep-value"}


_PROBE_MODULE = "tests.core.lazy_probe"
_PROBE = f"{_PROBE_MODULE}:Probe"


class TestRegisterLazy:

    def setup_method(self) -> None:
        sys.modules.pop(_PROBE_MODULE, None)

    def test_registering_imports_nothing(self):
        container = Container()

        container.register_lazy("probe", _PROBE)

        assert _PROBE_MODULE not in sys.modules
        assert not container.is_instantiated("probe")

    def test_resolving_imports_and_builds_it(self):
        container = Container()
        container.register_lazy("probe", _PROBE)

        assert type(container.resolve("probe")).__name__ == "Probe"
        assert _PROBE_MODULE in sys.modules
        assert container.is_instantiated("probe")

    def test_deps_are_resolved_in_order(self):
        container = Container()
        container.register("a", lambda c: "A")
        container.register("b", lambda c: "B")
        container.register_lazy("probe", _PROBE, "a", "b")

        assert container.resolve("probe").parts == ("A", "B")

    def test_instance_is_cached(self):
        container = Container()
        container.register_lazy("probe", _PROBE)

        assert container.resolve("probe") is container.resolve("probe")

    def test_target_without_a_name_is_rejected_on_resolve(self):
        container = Container()
        container.register_lazy("probe", _PROBE_MODULE)

        with pytest.raises(ValueError, match="module.path:Name"):
            container.resolve("probe")


class TestProvider:

    def test_does_not_build_until_called(self):
        container = Container()
        built = []
        container.register("svc", lambda c: built.append(1) or "value")

        provider = container.provider("svc")

        assert built == []
        assert not container.is_instantiated("svc")
        assert provider() == "value"
        assert provider() == "value"
        assert built == [1]

    def test_unknown_service_fails_when_wiring(self):
        with pytest.raises(KeyError, match="no_such"):
            Container().provider("no_such")
