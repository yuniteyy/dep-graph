"""Access to an npm-compatible registry using only the standard library."""
import json
import urllib.error
import urllib.request
from urllib.parse import quote

from .errors import ToolError

ACCEPT = ("application/vnd.npm.install-v1+json; q=1.0, "
          "application/json; q=0.8")
USER_AGENT = "depgraph/0.1"
TIMEOUT_SECONDS = 30
HTTP_NOT_FOUND = 404


class RegistryError(ToolError):
    """The registry cannot be queried or returned unusable data."""


class NotFoundError(RegistryError):
    """The requested package or version does not exist."""


def download(url, timeout, accept=ACCEPT):
    """Return the body of ``url``; translate failures to RegistryError."""
    try:
        request = urllib.request.Request(
            url, headers={"Accept": accept, "User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == HTTP_NOT_FOUND:
            raise NotFoundError(f"ресурс не найден: {url}") from None
        raise RegistryError(f"HTTP {exc.code} при запросе {url}") from None
    except (OSError, ValueError) as exc:
        raise RegistryError(
            f"не удалось выполнить запрос {url}: {exc}") from None


def fetch_json(url, timeout=TIMEOUT_SECONDS):
    """Download ``url`` and return the decoded JSON document."""
    body = download(url, timeout)
    try:
        return json.loads(body)
    except ValueError:
        raise RegistryError(f"некорректный JSON в ответе {url}") from None


class NpmRegistry:
    """Reads package metadata from a registry such as registry.npmjs.org."""

    def __init__(self, base_url, fetch=fetch_json):
        """Create a client for ``base_url``; ``fetch`` may be replaced."""
        self.base_url = base_url.rstrip("/")
        self._fetch = fetch
        self._cache = {}

    def packument(self, name):
        """Return the (abbreviated) metadata document of package ``name``."""
        if name not in self._cache:
            url = f"{self.base_url}/{quote(name, safe='@')}"
            try:
                data = self._fetch(url)
            except NotFoundError:
                raise NotFoundError(
                    f"пакет '{name}' не найден в репозитории") from None
            if not isinstance(data, dict):
                raise RegistryError(f"неожиданный ответ для пакета '{name}'")
            self._cache[name] = data
        return self._cache[name]

    def versions(self, name):
        """Return the ``version -> metadata`` mapping of package ``name``."""
        versions = self.packument(name).get("versions")
        if not isinstance(versions, dict):
            raise RegistryError(f"у пакета '{name}' нет списка версий")
        return versions

    def version_info(self, name, version):
        """Return the metadata of exactly ``name@version``."""
        versions = self.versions(name)
        if version not in versions:
            raise NotFoundError(
                f"версия {version} пакета '{name}' не найдена")
        return versions[version]

    def direct_dependencies(self, name, version):
        """Return ``{dependency name: version spec}`` of ``name@version``."""
        info = self.version_info(name, version)
        deps = info.get("dependencies") or {}
        if not isinstance(deps, dict):
            raise RegistryError(
                f"некорректные зависимости у {name}@{version}")
        return {str(key): str(value) for key, value in deps.items()}
