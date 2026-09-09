/* Functional adapter for sphinx-data-viewer: keep the upstream widget, but reveal
   the first three JSON levels by default. Upstream supports only collapsed/all. */
(function () {
  "use strict";

  const DEFAULT_EXPAND_DEPTH = 3;

  function expandToDepth(node, maxDepth) {
    if (!node || node.depth >= maxDepth || !node.children?.length) {
      return;
    }

    node.isExpanded = true;
    node.el
      ?.querySelector(".fa-caret-right")
      ?.classList.replace("fa-caret-right", "fa-caret-down");
    node.children.forEach((child) => {
      child.el?.classList.remove("hide");
      expandToDepth(child, maxDepth);
    });
  }

  function revealViewer(container) {
    if (
      container.dataset.expand === "True" ||
      typeof window.JsonView === "undefined"
    ) {
      return;
    }

    const raw = container.getAttribute("data-sdv");
    if (!raw) {
      return;
    }

    try {
      const tree = window.JsonView.createTree(raw);
      container.replaceChildren();
      window.JsonView.render(tree, container);
      expandToDepth(tree, DEFAULT_EXPAND_DEPTH);
    } catch (_error) {
      // Keep sphinx-data-viewer's own rendered fallback/error state intact.
    }
  }

  function revealDataViewers() {
    document
      .querySelectorAll(".sphinx-data-viewer .sdv-data")
      .forEach(revealViewer);
  }

  if (document.readyState === "complete") {
    revealDataViewers();
  } else {
    window.addEventListener("load", revealDataViewers, { once: true });
  }
})();
