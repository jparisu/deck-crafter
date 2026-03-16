"""Local web interface for authoring configuration files and previewing cards."""

# ruff: noqa: E501

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from deck_crafter.application import generate_deck_from_project, preview_card
from deck_crafter.configuration import ConfigurationLoader, create_default_project


class VisualInterfaceServer:
    """Serve a lightweight browser UI for editing project configurations."""

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        configuration_file: str | Path | None = None,
    ) -> None:
        """Store the network binding and optional initial configuration file."""
        self.host = host
        self.port = port
        self.configuration_file = (
            None if configuration_file is None else Path(configuration_file).expanduser().resolve()
        )
        self.project = (
            create_default_project()
            if self.configuration_file is None
            else ConfigurationLoader.from_file(self.configuration_file)
        )

    def serve_forever(self) -> None:
        """Start the local HTTP server and block until interrupted."""
        with self._build_http_server() as server:
            server.serve_forever()

    @contextmanager
    def _build_http_server(self) -> Iterator[ThreadingHTTPServer]:
        """Create the HTTP server instance used by the visual editor."""
        outer = self

        class Handler(BaseHTTPRequestHandler):
            """Request handler bound to one visual interface server instance."""

            def do_GET(self) -> None:  # noqa: N802
                """Serve the HTML shell or JSON API endpoints."""
                if self.path == "/":
                    self._send_html(_index_html())
                    return
                if self.path.startswith("/api/project"):
                    payload = {
                        "configuration_file": (
                            None
                            if outer.configuration_file is None
                            else str(outer.configuration_file)
                        ),
                        "project": outer.project.to_dict(),
                    }
                    self._send_json(payload)
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:  # noqa: N802
                """Handle JSON API operations from the browser UI."""
                data = self._read_json_body()
                if self.path == "/api/project/load":
                    configuration_file = Path(str(data["path"])).expanduser().resolve()
                    outer.project = ConfigurationLoader.from_file(configuration_file)
                    outer.configuration_file = configuration_file
                    self._send_json(
                        {
                            "configuration_file": str(configuration_file),
                            "project": outer.project.to_dict(),
                        }
                    )
                    return
                if self.path == "/api/project/save":
                    configuration_file = Path(str(data["path"])).expanduser().resolve()
                    outer.project = ConfigurationLoader.from_dict(
                        data["project"],
                        base_path=configuration_file.parent,
                    )
                    outer.configuration_file = configuration_file
                    saved_path = ConfigurationLoader.dump(outer.project, configuration_file)
                    self._send_json({"saved_path": str(saved_path)})
                    return
                if self.path == "/api/preview":
                    project = ConfigurationLoader.from_dict(
                        data["project"],
                        base_path=None
                        if outer.configuration_file is None
                        else outer.configuration_file.parent,
                    )
                    payload = preview_card(
                        project,
                        card_id=str(data["card_id"]),
                        side=str(data.get("side", "front")),
                    )
                    self._send_json(payload)
                    return
                if self.path == "/api/generate":
                    project = ConfigurationLoader.from_dict(
                        data["project"],
                        base_path=None
                        if outer.configuration_file is None
                        else outer.configuration_file.parent,
                    )
                    outputs = generate_deck_from_project(
                        project, compile_pdf=bool(data.get("compile_pdf", True))
                    )
                    self._send_json({"outputs": [str(path) for path in outputs]})
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def log_message(self, format: str, *args: object) -> None:
                """Silence the default request logging noise."""
                return None

            def _read_json_body(self) -> dict[str, Any]:
                """Read and decode the JSON request payload."""
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw.decode("utf-8"))
                if not isinstance(body, dict):
                    raise TypeError("Expected a JSON object request body.")
                return body

            def _send_json(self, payload: dict[str, Any]) -> None:
                """Send a JSON response."""
                response = json.dumps(payload).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def _send_html(self, html: str) -> None:
                """Send an HTML response."""
                response = html.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        server = ThreadingHTTPServer((self.host, self.port), Handler)
        try:
            yield server
        finally:
            server.server_close()


def serve_visual_interface(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    configuration_file: str | Path | None = None,
) -> None:
    """Start the local visual editor server."""
    VisualInterfaceServer(
        host=host, port=port, configuration_file=configuration_file
    ).serve_forever()


def _index_html() -> str:
    """Return the single-page HTML application served by the visual editor."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Deck Crafter</title>
  <style>
    :root {
      --page: #f1ece2;
      --ink: #1d2430;
      --panel: #fffdf8;
      --accent: #9b4d16;
      --line: #d7c5ae;
      --muted: #675e54;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(155,77,22,0.12), transparent 28%),
        linear-gradient(180deg, #f7f3ea 0%, #efe5d3 100%);
    }
    header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.65);
      backdrop-filter: blur(10px);
    }
    header h1 {
      margin: 0;
      font-size: 1.5rem;
    }
    header p {
      margin: 6px 0 0;
      color: var(--muted);
    }
    main {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 18px;
      padding: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 12px 30px rgba(29,36,48,0.08);
      padding: 18px;
    }
    .stack { display: grid; gap: 12px; }
    label { display: grid; gap: 6px; font-size: 0.9rem; }
    input, select, textarea, button {
      font: inherit;
      border-radius: 10px;
      border: 1px solid var(--line);
      padding: 10px 12px;
      background: white;
      color: var(--ink);
    }
    textarea { min-height: 110px; resize: vertical; }
    button {
      cursor: pointer;
      background: var(--accent);
      color: white;
      border: none;
    }
    button.secondary {
      background: #314052;
    }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .preview-shell {
      display: grid;
      grid-template-columns: minmax(280px, 420px) 1fr;
      gap: 18px;
      align-items: start;
    }
    .preview-card {
      position: relative;
      border-radius: 22px;
      overflow: hidden;
      border: 2px solid #b58b63;
      background: white;
      box-shadow: 0 20px 34px rgba(29,36,48,0.12);
    }
    .preview-node {
      position: absolute;
      overflow: hidden;
      border: 1px dashed rgba(49,64,82,0.25);
      padding: 4px;
      font-size: 12px;
    }
    .preview-node.selected {
      outline: 3px solid rgba(155,77,22,0.55);
      border-style: solid;
    }
    .node-list {
      display: grid;
      gap: 8px;
      max-height: 260px;
      overflow: auto;
    }
    .node-row {
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      cursor: pointer;
      background: #fff;
    }
    .node-row.active {
      border-color: var(--accent);
      background: #fff7f1;
    }
    .muted { color: var(--muted); font-size: 0.9rem; }
    @media (max-width: 960px) {
      main, .preview-shell {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>Deck Crafter</h1>
    <p>Interactive project editor with YAML save/load, card preview, and PDF generation.</p>
  </header>
  <main>
    <section class="panel stack">
      <label>Configuration file
        <input id="configPath" placeholder="/path/to/project.yaml">
      </label>
      <div class="toolbar">
        <button id="loadButton" class="secondary">Load YAML</button>
        <button id="saveButton">Save YAML</button>
      </div>
      <label>Layout
        <select id="layoutSelect"></select>
      </label>
      <label>Card
        <select id="cardSelect"></select>
      </label>
      <label>Side
        <select id="sideSelect">
          <option value="front">Front</option>
          <option value="back">Back</option>
        </select>
      </label>
      <div class="toolbar">
        <button id="addTextButton" class="secondary">Add Text</button>
        <button id="addImageButton" class="secondary">Add Image</button>
        <button id="addColorButton" class="secondary">Add Color</button>
      </div>
      <label>Project YAML
        <textarea id="yamlPreview" readonly></textarea>
      </label>
      <button id="generateButton">Generate PDF</button>
      <div id="status" class="muted"></div>
    </section>

    <section class="panel stack">
      <div class="preview-shell">
        <div>
          <div id="previewCard" class="preview-card"></div>
          <p class="muted">Select a node on the right to edit its rectangle and bound value.</p>
        </div>
        <div class="stack">
          <div>
            <strong>Nodes</strong>
            <div id="nodeList" class="node-list"></div>
          </div>
          <div class="stack">
            <strong>Selected node</strong>
            <label>ID
              <input id="nodeId">
            </label>
            <label>X
              <input id="nodeX" type="number" step="0.01">
            </label>
            <label>Y
              <input id="nodeY" type="number" step="0.01">
            </label>
            <label>Width
              <input id="nodeWidth" type="number" step="0.01">
            </label>
            <label>Height
              <input id="nodeHeight" type="number" step="0.01">
            </label>
            <label>Value
              <textarea id="nodeValue"></textarea>
            </label>
            <div class="toolbar">
              <button id="applyButton">Apply Changes</button>
              <button id="removeButton" class="secondary">Remove Node</button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const state = {
      project: null,
      preview: null,
      selectedNodeId: null,
    };

    const byId = (id) => document.getElementById(id);

    async function fetchJson(url, options = {}) {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    }

    function refreshSelectors() {
      const layouts = state.project.layouts;
      const cards = state.project.cards;
      byId("layoutSelect").innerHTML = layouts.map((layout) =>
        `<option value="${layout.id}">${layout.name}</option>`
      ).join("");
      byId("cardSelect").innerHTML = cards.map((card) =>
        `<option value="${card.id}">${card.name}</option>`
      ).join("");
      const card = cards[0];
      if (card) {
        byId("cardSelect").value = card.id;
        byId("layoutSelect").value = card.layout_id;
      }
    }

    async function loadProjectFromServer() {
      const data = await fetchJson("/api/project");
      state.project = data.project;
      if (data.configuration_file) {
        byId("configPath").value = data.configuration_file;
      }
      refreshSelectors();
      updateYamlPreview();
      await refreshPreview();
    }

    function updateYamlPreview() {
      byId("yamlPreview").value = JSON.stringify(state.project, null, 2);
    }

    function activeCard() {
      return state.project.cards.find((card) => card.id === byId("cardSelect").value);
    }

    function activeLayout() {
      return state.project.layouts.find((layout) => layout.id === byId("layoutSelect").value);
    }

    function activeRoot() {
      const side = byId("sideSelect").value;
      const layout = activeLayout();
      return side === "front" ? layout.front_root : layout.back_root;
    }

    function walkNodes(node, output = []) {
      output.push(node);
      if (node.type === "container") {
        for (const child of node.children) {
          walkNodes(child, output);
        }
      }
      return output;
    }

    function findNode(node, nodeId) {
      if (node.id === nodeId) {
        return node;
      }
      if (node.type === "container") {
        for (const child of node.children) {
          const result = findNode(child, nodeId);
          if (result) {
            return result;
          }
        }
      }
      return null;
    }

    function removeNode(node, nodeId) {
      if (node.type !== "container") {
        return false;
      }
      const index = node.children.findIndex((child) => child.id === nodeId);
      if (index >= 0) {
        node.children.splice(index, 1);
        return true;
      }
      return node.children.some((child) => removeNode(child, nodeId));
    }

    function ensureSelectedNode() {
      const root = activeRoot();
      if (!state.selectedNodeId) {
        const nodes = walkNodes(root, []);
        state.selectedNodeId = nodes[1] ? nodes[1].id : root.id;
      }
      return findNode(root, state.selectedNodeId);
    }

    function applyNodeForm() {
      const node = ensureSelectedNode();
      if (!node) {
        return;
      }
      node.id = byId("nodeId").value.trim() || node.id;
      node.rect.x.value = Number(byId("nodeX").value);
      node.rect.y.value = Number(byId("nodeY").value);
      node.rect.width.value = Number(byId("nodeWidth").value);
      node.rect.height.value = Number(byId("nodeHeight").value);
      const card = activeCard();
      const sideKey = byId("sideSelect").value === "front" ? "values_front" : "values_back";
      const rawValue = byId("nodeValue").value;
      if (node.type === "text") {
        card[sideKey][node.id] = { type: "text", text: rawValue };
      } else if (node.type === "image") {
        card[sideKey][node.id] = { type: "image", path: rawValue };
      } else if (node.type === "color") {
        card[sideKey][node.id] = { type: "color", color: rawValue };
      }
      updateYamlPreview();
    }

    function fillNodeForm() {
      const node = ensureSelectedNode();
      if (!node) {
        return;
      }
      byId("nodeId").value = node.id;
      byId("nodeX").value = node.rect.x.value;
      byId("nodeY").value = node.rect.y.value;
      byId("nodeWidth").value = node.rect.width.value;
      byId("nodeHeight").value = node.rect.height.value;
      const card = activeCard();
      const sideKey = byId("sideSelect").value === "front" ? "values_front" : "values_back";
      const value = card[sideKey][node.id] || {};
      byId("nodeValue").value = value.text || value.path || value.color || "";
    }

    async function refreshPreview() {
      const card = activeCard();
      if (!card) {
        return;
      }
      byId("layoutSelect").value = card.layout_id;
      state.preview = await fetchJson("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project: state.project,
          card_id: card.id,
          side: byId("sideSelect").value,
        }),
      });
      renderPreview();
      renderNodeList();
      fillNodeForm();
    }

    function renderPreview() {
      const preview = state.preview;
      const root = byId("previewCard");
      const width = 360;
      const scale = width / preview.card_rect.width;
      root.style.width = `${preview.card_rect.width * scale}px`;
      root.style.height = `${preview.card_rect.height * scale}px`;
      root.innerHTML = "";
      for (const node of preview.nodes) {
        const element = document.createElement("div");
        element.className = "preview-node" + (node.id === state.selectedNodeId ? " selected" : "");
        element.style.left = `${node.rect.x * scale}px`;
        element.style.top = `${node.rect.y * scale}px`;
        element.style.width = `${node.rect.width * scale}px`;
        element.style.height = `${node.rect.height * scale}px`;
        element.style.opacity = node.opacity;
        element.style.zIndex = node.z_index;
        if (node.node_type === "color" && node.color) {
          element.style.background = node.color;
        }
        if (node.node_type === "image" && node.image_path) {
          element.style.backgroundImage = `url(${node.image_path})`;
          element.style.backgroundSize = node.meta && node.meta.fit === "contain" ? "contain" : "cover";
          element.style.backgroundPosition = "center";
          element.style.backgroundRepeat = "no-repeat";
        }
        if (node.node_type === "text") {
          element.style.color = node.color || "#111";
          element.style.display = "flex";
          element.style.alignItems = "flex-start";
          element.style.justifyContent = node.meta && node.meta.align === "center" ? "center" : "flex-start";
          element.textContent = node.text || "";
        }
        if (node.node_type === "bleed") {
          element.style.border = `2px solid ${node.color || "#000"}`;
          element.style.background = "transparent";
        }
        element.onclick = () => {
          state.selectedNodeId = node.id;
          renderPreview();
          renderNodeList();
          fillNodeForm();
        };
        root.appendChild(element);
      }
    }

    function renderNodeList() {
      const root = activeRoot();
      const nodes = walkNodes(root, []).filter((node) => node.type !== "container");
      byId("nodeList").innerHTML = nodes.map((node) =>
        `<div class="node-row ${node.id === state.selectedNodeId ? "active" : ""}" data-node-id="${node.id}">
          <strong>${node.id}</strong><br><span class="muted">${node.type}</span>
        </div>`
      ).join("");
      for (const element of byId("nodeList").querySelectorAll("[data-node-id]")) {
        element.onclick = () => {
          state.selectedNodeId = element.dataset.nodeId;
          renderNodeList();
          renderPreview();
          fillNodeForm();
        };
      }
    }

    function addNode(type) {
      const root = activeRoot();
      const baseId = `${type}_${Date.now()}`;
      const node = {
        type,
        id: baseId,
        side: byId("sideSelect").value,
        rect: {
          x: { mode: "relative", value: 0.1, ref: "card", unit: "mm" },
          y: { mode: "relative", value: 0.1, ref: "card", unit: "mm" },
          width: { mode: "relative", value: 0.8, ref: "card", unit: "mm" },
          height: { mode: "relative", value: type === "text" ? 0.18 : 0.35, ref: "card", unit: "mm" },
          anchor: "top_left",
        },
        z_index: 0,
        opacity: 1.0,
        rotation_deg: 0.0,
      };
      if (type === "text") {
        Object.assign(node, {
          font_family: "Helvetica",
          font_size_pt: 12,
          font_color: "#111111",
          align: "left",
          wrap: true,
          line_height: 1.2,
        });
      } else if (type === "image") {
        Object.assign(node, { fit: "cover", crop_anchor: "center", clip: true });
      } else if (type === "color") {
        Object.assign(node, { color: "#dddddd" });
      }
      root.children.push(node);
      state.selectedNodeId = baseId;
      updateYamlPreview();
      refreshPreview();
    }

    async function saveProject() {
      const path = byId("configPath").value.trim();
      if (!path) {
        throw new Error("Provide a configuration path first.");
      }
      const response = await fetchJson("/api/project/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, project: state.project }),
      });
      byId("status").textContent = `Saved ${response.saved_path}`;
    }

    async function loadProjectFromPath() {
      const path = byId("configPath").value.trim();
      if (!path) {
        throw new Error("Provide a configuration path first.");
      }
      const response = await fetchJson("/api/project/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      state.project = response.project;
      refreshSelectors();
      updateYamlPreview();
      await refreshPreview();
      byId("status").textContent = `Loaded ${response.configuration_file}`;
    }

    async function generatePdf() {
      const response = await fetchJson("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: state.project, compile_pdf: true }),
      });
      byId("status").textContent = `Generated ${response.outputs.join(", ")}`;
    }

    byId("cardSelect").addEventListener("change", refreshPreview);
    byId("sideSelect").addEventListener("change", refreshPreview);
    byId("layoutSelect").addEventListener("change", refreshPreview);
    byId("applyButton").addEventListener("click", async () => {
      applyNodeForm();
      await refreshPreview();
    });
    byId("removeButton").addEventListener("click", async () => {
      const root = activeRoot();
      if (state.selectedNodeId && removeNode(root, state.selectedNodeId)) {
        state.selectedNodeId = null;
        updateYamlPreview();
        await refreshPreview();
      }
    });
    byId("addTextButton").addEventListener("click", () => addNode("text"));
    byId("addImageButton").addEventListener("click", () => addNode("image"));
    byId("addColorButton").addEventListener("click", () => addNode("color"));
    byId("saveButton").addEventListener("click", () => saveProject().catch(showError));
    byId("loadButton").addEventListener("click", () => loadProjectFromPath().catch(showError));
    byId("generateButton").addEventListener("click", () => generatePdf().catch(showError));

    function showError(error) {
      byId("status").textContent = error.message;
    }

    loadProjectFromServer().catch(showError);
  </script>
</body>
</html>"""
