"""PlantUML text of a dependency graph and its rendering to PNG."""
import base64
import os
import subprocess
import zlib

from .errors import ToolError
from .graph import find_cycles
from .registry import RegistryError, download

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STD_ALPHABET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                "0123456789+/")
PUML_ALPHABET = ("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                 "abcdefghijklmnopqrstuvwxyz-_")
ENCODE_TABLE = str.maketrans(STD_ALPHABET, PUML_ALPHABET)
DEFLATE_LEVEL = 9
GROUP_SIZE = 3
RAW_DEFLATE = -zlib.MAX_WBITS
MAX_URL_LENGTH = 8000
RENDER_TIMEOUT = 120
PNG_ACCEPT = "image/png"
ROOT_STYLE = "#LightSkyBlue"
FRONTIER_STYLE = "#WhiteSmoke;line.dashed"
CYCLE_ARROW = "-[#red]->"
PLAIN_ARROW = "-->"


class RenderError(ToolError):
    """The PNG image cannot be produced or saved."""


def _cycle_edges(graph):
    """Return the set of edges that belong to some cycle."""
    edges = set()
    for cycle in find_cycles(graph):
        edges.update(zip(cycle, cycle[1:]))
    return edges


def _node_line(node, alias, graph):
    """Return the PlantUML declaration of one node."""
    style = ""
    if node == graph.root:
        style = f" {ROOT_STYLE}"
    elif node in graph.frontier:
        style = f" {FRONTIER_STYLE}"
    return f'rectangle "{node}" as {alias}{style}'


def to_plantuml(graph, title, reverse=False):
    """Return the PlantUML source of ``graph``.

    The root is highlighted, nodes that were not expanded are dashed and
    edges of cycles are red. In reverse mode arrows are drawn from a
    package to the package it depends on, as in the real dependency
    direction.
    """
    aliases = {node: f"n{index}" for index, node in
               enumerate(graph.nodes())}
    lines = ["@startuml", f"title {title}", "skinparam shadowing false"]
    lines.extend(_node_line(node, aliases[node], graph)
                 for node in graph.nodes())
    cyclic = _cycle_edges(graph)
    for source, target in graph.edge_list():
        arrow = CYCLE_ARROW if (source, target) in cyclic else PLAIN_ARROW
        left, right = (target, source) if reverse else (source, target)
        lines.append(f"{aliases[left]} {arrow} {aliases[right]}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def encode(text):
    """Encode PlantUML source for a server URL (deflate + own base64)."""
    packer = zlib.compressobj(DEFLATE_LEVEL, zlib.DEFLATED, RAW_DEFLATE)
    data = packer.compress(text.encode("utf-8")) + packer.flush()
    data += bytes(-len(data) % GROUP_SIZE)
    return base64.b64encode(data).decode("ascii").translate(ENCODE_TABLE)


def check_png(data, source):
    """Return ``data`` if it is a PNG image, otherwise raise."""
    if not data.startswith(PNG_SIGNATURE):
        raise RenderError(f"{source} вернул не PNG-изображение")
    return data


def render_with_jar(text, jar):
    """Render ``text`` to PNG bytes with a local ``plantuml.jar``."""
    command = ["java", "-Djava.awt.headless=true", "-jar", jar,
               "-charset", "UTF-8", "-tpng", "-pipe"]
    try:
        done = subprocess.run(command, input=text.encode("utf-8"),
                              capture_output=True, timeout=RENDER_TIMEOUT)
    except FileNotFoundError:
        raise RenderError("не найдена Java для запуска PlantUML") from None
    except subprocess.TimeoutExpired:
        raise RenderError("PlantUML не завершился за отведённое время") \
            from None
    if done.returncode:
        message = done.stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"ошибка PlantUML: {message}")
    return check_png(done.stdout, "PlantUML")


def render_with_server(text, server):
    """Render ``text`` to PNG bytes with a PlantUML web server."""
    url = f"{server.rstrip('/')}/png/{encode(text)}"
    if len(url) > MAX_URL_LENGTH:
        raise RenderError(
            "граф слишком велик для PlantUML-сервера, "
            "используйте --plantuml-jar или уменьшите --max-depth")
    try:
        data = download(url, RENDER_TIMEOUT, accept=PNG_ACCEPT)
    except RegistryError as exc:
        raise RenderError(f"PlantUML-сервер недоступен: {exc}") from None
    return check_png(data, "PlantUML-сервер")


def render_png(text, jar, server):
    """Render ``text`` with the jar if given, otherwise with the server."""
    if jar:
        return render_with_jar(text, jar)
    return render_with_server(text, server)


def write_file(path, data):
    """Write bytes or text to ``path``; report failures as RenderError."""
    mode, kwargs = ("wb", {}) if isinstance(data, bytes) else (
        "w", {"encoding": "utf-8"})
    try:
        with open(path, mode, **kwargs) as handle:
            handle.write(data)
    except OSError as exc:
        raise RenderError(
            f"не удалось записать {path}: {exc.strerror}") from None


def puml_path(output):
    """Return the name of the ``.puml`` file next to the image."""
    return os.path.splitext(output)[0] + ".puml"
