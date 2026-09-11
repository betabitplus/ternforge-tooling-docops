"""Interactive specification-health map projection."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from ternforge_docops._internal.sphinx.review_common import (
    need_sort_key,
    need_url,
    normalize_ids,
)
from ternforge_docops._internal.sphinx.specification_health import (
    SpecificationHealth,
    project_specification_health,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_SPEC_TYPES = frozenset({"goal", "feature", "req", "treq"})
_KIND_LABELS = {
    "goal": "Goal",
    "feature": "Capability",
    "req": "Requirement",
    "treq": "Technical requirement",
}
_EVIDENCE_LABELS = {
    "impl": "Implementation",
    "bdd": "Behavior scenario",
    "unit": "Unit check",
    "property": "Property check",
    "integration": "Integration check",
    "e2e": "End-to-end check",
}
_HEALTH_COLORS = {
    "good": "#2f8f5b",
    "gap": "#c84b4b",
    "warning": "#d39b2a",
    "inactive": "#7b818a",
    "neutral": "#667a99",
}
_PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def _health_state(
    state: SpecificationHealth | None,
    need: Mapping[str, object],
) -> tuple[str, str]:
    """Return compact health class and human reason for one specification node."""
    status = str(need.get("status") or "")
    result = ("warning", "Needs attention")
    if status in {"draft", "deprecated"}:
        result = ("inactive", status.title())
    elif state is None:
        result = ("neutral", "No derived health state")
    elif state.deep_covered:
        result = ("good", "Current proof is complete")
    elif state.missing_evidence:
        missing = ", ".join(
            _EVIDENCE_LABELS.get(kind, kind.replace("_", " ").title())
            for kind in state.missing_evidence
        )
        result = ("gap", f"Missing {missing}")
    elif state.gap_reason:
        result = ("gap", state.gap_reason)
    elif state.blocked_by:
        result = ("gap", f"Blocked by {len(state.blocked_by)} downstream gap(s)")
    return result


def _parent_map(
    specs: Mapping[str, Mapping[str, object]],
) -> dict[str, str]:
    """Build the single authored hierarchy used by the review projection."""
    parent: dict[str, str] = {}
    for need_id, need in specs.items():
        candidates = [
            item for item in normalize_ids(need.get("derives")) if item in specs
        ]
        if candidates:
            parent[need_id] = candidates[0]
    return parent


def _leaf_counts(
    children: Mapping[str, list[str]],
    node_id: str,
) -> int:
    """Return leaf count for stable treemap sizing."""
    node_children = children.get(node_id, [])
    if not node_children:
        return 1
    return sum(_leaf_counts(children, child) for child in node_children)


def specification_map_html(
    app: Sphinx,
    fromdocname: str,
    needs: Mapping[str, Mapping[str, object]],
) -> str:
    """Render one screen-sized Plotly treemap colored by derived health."""
    specs = {
        need_id: need
        for need_id, need in needs.items()
        if str(need.get("type") or "") in _SPEC_TYPES
    }
    health = project_specification_health(needs.values())
    parent = _parent_map(specs)
    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []
    for need_id in specs:
        parent_id = parent.get(need_id)
        if parent_id:
            children[parent_id].append(need_id)
        else:
            roots.append(need_id)

    root_id = "__PRODUCT_INTENT__"
    children[root_id] = sorted(roots, key=lambda value: need_sort_key(specs[value]))
    for node_children in children.values():
        node_children.sort(key=lambda value: need_sort_key(specs[value]))

    ids = [root_id]
    labels = ["Product intent"]
    parents = [""]
    values = [_leaf_counts(children, root_id)]
    colors = ["#667a99"]
    custom: list[list[str]] = [["Overview", "Specification health", "", "", ""]]

    for need_id, need in sorted(specs.items(), key=lambda item: need_sort_key(item[1])):
        state, detail = _health_state(health.get(need_id), need)
        need_type = str(need.get("type") or "")
        ids.append(need_id)
        labels.append(str(need.get("title") or need_id))
        parents.append(parent.get(need_id, root_id))
        values.append(_leaf_counts(children, need_id))
        colors.append(_HEALTH_COLORS[state])
        custom.append(
            [
                _KIND_LABELS.get(need_type, need_type.title()),
                detail,
                need_url(app, fromdocname, need),
                need_id,
                state,
            ]
        )

    data = {
        "type": "treemap",
        "ids": ids,
        "labels": labels,
        "parents": parents,
        "values": values,
        "branchvalues": "total",
        "textinfo": "label",
        "textfont": {"size": 14},
        "insidetextfont": {"color": "#ffffff"},
        "marker": {
            "colors": colors,
            "line": {"width": 2, "color": "rgba(255,255,255,.72)"},
        },
        "customdata": custom,
        "hovertemplate": (
            "<b>%{label}</b><br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>"
        ),
        "pathbar": {"visible": False},
        "sort": False,
    }
    layout = {
        "margin": {"t": 8, "l": 8, "r": 8, "b": 8},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "system-ui, -apple-system, BlinkMacSystemFont, sans-serif"},
        "uirevision": "ternforge-specification-map",
    }
    config = {
        "responsive": True,
        "displayModeBar": False,
        "displaylogo": False,
    }

    return f"""
<div class="ternforge-specification-map-shell">
  <div class="ternforge-health-legend" aria-label="Specification health legend">
    <span><i class="is-good"></i>Complete</span>
    <span><i class="is-gap"></i>Gap</span>
    <span><i class="is-warning"></i>Needs attention</span>
    <span><i class="is-inactive"></i>Inactive</span>
  </div>
  <div id="ternforge-specification-map" class="ternforge-specification-map"></div>
</div>
<script src="{_PLOTLY_CDN}"></script>
<script>
(function () {{
  const element = document.getElementById("ternforge-specification-map");
  const data = [{json.dumps(data)}];
  const layout = {json.dumps(layout)};
  const config = {json.dumps(config)};

  function sizeMap() {{
    const available = window.innerHeight - element.getBoundingClientRect().top - 16;
    element.style.height = Math.max(384, available) + "px";
  }}

  function render() {{
    if (!element || typeof Plotly === "undefined") {{
      return;
    }}
    sizeMap();
    const rootStyle = getComputedStyle(document.documentElement);
    layout.font.color = getComputedStyle(document.body).color;
    const border = rootStyle.getPropertyValue("--pst-color-border").trim();
    if (border) {{
      data[0].marker.line.color = border;
    }}
    Plotly.newPlot(element, data, layout, config);
    element.on("plotly_treemapclick", function (eventData) {{
      const point = eventData && eventData.points && eventData.points[0];
      const target = point && point.customdata && point.customdata[2];
      if (target) {{
        window.location.href = target;
      }}
      return false;
    }});
    window.addEventListener("resize", function () {{
      sizeMap();
      Plotly.Plots.resize(element);
    }});
  }}

  if (typeof Plotly !== "undefined") {{
    render();
  }} else {{
    const script = document.querySelector('script[src*="plotly"]');
    if (script) {{
      script.addEventListener("load", render, {{ once: true }});
    }}
  }}
}})();
</script>
"""
