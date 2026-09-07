/* Progressive disclosure for retained Engineering Experiment evidence. */
(function () {
  "use strict";

  function childContaining(children, selector) {
    return children.find((child) => child.querySelector(selector));
  }

  function activateTab(tablist, panels, selected) {
    const tabs = Array.from(tablist.querySelectorAll("[role='tab']"));
    tabs.forEach((tab, index) => {
      const active = index === selected;
      tab.setAttribute("aria-selected", active ? "true" : "false");
      panels[index].hidden = !active;
    });
  }

  function renderJsonTree(rawResult) {
    const code = rawResult ? rawResult.querySelector("pre code") : null;
    if (!code || typeof window.JsonView === "undefined") {
      return rawResult;
    }
    try {
      const viewer = document.createElement("div");
      viewer.className = "sphinx-data-viewer exp-json-viewer";
      const target = document.createElement("div");
      target.className = "exp-json-tree";
      const tree = window.JsonView.createTree(code.textContent);
      window.JsonView.render(tree, target);
      viewer.appendChild(target);
      return viewer;
    } catch (_error) {
      return rawResult;
    }
  }

  function technicalDetails(codeOutput, rawResult) {
    if (!codeOutput && !rawResult) {
      return null;
    }

    const details = document.createElement("details");
    details.className = "exp-technical-details";
    const summary = document.createElement("summary");
    summary.textContent = "Technical details";
    details.appendChild(summary);

    const body = document.createElement("div");
    body.className = "exp-technical-body";
    details.appendChild(body);

    const panels = [];
    const labels = [];
    if (codeOutput) {
      labels.push("Actual code");
      panels.push(codeOutput);
    }
    if (rawResult) {
      labels.push("Raw result");
      const rawPanel = document.createElement("div");
      rawPanel.className = "exp-tech-panel";
      rawPanel.appendChild(rawResult);
      panels.push(rawPanel);
    }

    if (panels.length === 1) {
      body.appendChild(panels[0]);
      return details;
    }

    const tablist = document.createElement("div");
    tablist.className = "exp-tech-tabs";
    tablist.setAttribute("role", "tablist");
    labels.forEach((label, index) => {
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = "exp-tech-tab";
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", index === 0 ? "true" : "false");
      tab.textContent = label;
      tab.addEventListener("click", () => activateTab(tablist, panels, index));
      tablist.appendChild(tab);
    });
    body.appendChild(tablist);
    panels.forEach((panel, index) => {
      panel.classList.add("exp-tech-panel");
      panel.hidden = index !== 0;
      body.appendChild(panel);
    });
    return details;
  }

  function enhanceEvidence(cell) {
    const output = cell.querySelector(":scope > .cell_output");
    if (!output || output.dataset.expEnhanced === "true") {
      return;
    }
    const children = Array.from(output.children);
    const inputOutput = childContaining(children, ".exp-input-panel");
    const codeOutput = childContaining(children, ".exp-code-panel");
    const resultOutput = childContaining(children, ".exp-result-panel");
    if (!inputOutput || !resultOutput) {
      return;
    }

    const inputIndex = children.indexOf(inputOutput);
    const codeIndex = codeOutput ? children.indexOf(codeOutput) : children.length;
    const resultIndex = children.indexOf(resultOutput);
    const mediaOutputs = children.filter((child, index) => {
      if (index <= inputIndex || index >= codeIndex || index === resultIndex) {
        return false;
      }
      return !child.querySelector(".exp-code-panel, .exp-result-panel");
    });

    const rawResult = resultOutput.querySelector(".exp-raw-result");
    if (rawResult) {
      rawResult.remove();
      rawResult.open = true;
      const rawSummary = rawResult.querySelector(":scope > summary");
      if (rawSummary) {
        rawSummary.remove();
      }
    }

    const grid = document.createElement("div");
    grid.className = "exp-evidence-grid";
    const inputColumn = document.createElement("div");
    inputColumn.className = "exp-evidence-column exp-evidence-input";
    const resultColumn = document.createElement("div");
    resultColumn.className = "exp-evidence-column exp-evidence-result";
    inputColumn.appendChild(inputOutput);
    mediaOutputs.forEach((media) => inputColumn.appendChild(media));
    resultColumn.appendChild(resultOutput);
    grid.append(inputColumn, resultColumn);

    const technical = technicalDetails(codeOutput, renderJsonTree(rawResult));
    output.replaceChildren(grid);
    if (technical) {
      output.appendChild(technical);
    }
    output.dataset.expEnhanced = "true";
  }

  function moveAnswerNearQuestion() {
    const question = document.querySelector("section#question");
    const conclusion = document.querySelector("section#conclusion");
    if (!question || !conclusion) {
      return;
    }
    const setup = question.querySelector(":scope > .cell.tag_exp-setup");
    const heading = conclusion.querySelector(":scope > h2");
    if (heading?.firstChild) {
      heading.firstChild.textContent = "Answer";
    }
    conclusion.classList.add("exp-answer");
    question.insertAdjacentElement("afterend", conclusion);
    if (setup) {
      conclusion.insertAdjacentElement("afterend", setup);
    }

    const tocQuestionLink = document.querySelector('nav a[href="#question"]');
    const tocConclusionLink = document.querySelector('nav a[href="#conclusion"]');
    if (tocConclusionLink) {
      tocConclusionLink.textContent = "Answer";
      const questionItem = tocQuestionLink?.closest("li");
      const conclusionItem = tocConclusionLink.closest("li");
      if (questionItem && conclusionItem) {
        questionItem.insertAdjacentElement("afterend", conclusionItem);
      }
    }
  }

  function renderProvenance() {
    const answer = document.querySelector("section#conclusion.exp-answer");
    const date = document.querySelector('meta[name="ternforge-exp-date"]')?.content;
    const informs = Array.from(
      document.querySelectorAll('meta[name="ternforge-exp-inform"]'),
    );
    const sourceLink = Array.from(document.querySelectorAll("a[href]")).find((link) =>
      /\/(?:blob|tree)\/[0-9a-f]{40}\//.test(link.href),
    );
    const revision = sourceLink?.href.match(/\/(?:blob|tree)\/([0-9a-f]{40})\//)?.[1];
    if (!answer || (!date && !revision && informs.length === 0)) {
      return;
    }

    const provenance = document.createElement("div");
    provenance.className = "exp-provenance";
    if (date) {
      const captured = document.createElement("span");
      captured.textContent = `Captured ${date}`;
      provenance.appendChild(captured);
    }
    if (revision && sourceLink) {
      const source = document.createElement("a");
      source.href = sourceLink.href;
      source.textContent = `source @ ${revision.slice(0, 10)}`;
      provenance.appendChild(source);
    }
    if (informs.length) {
      const group = document.createElement("span");
      group.append("Informs ");
      informs.forEach((meta, index) => {
        if (index) {
          group.append(" · ");
        }
        const id = meta.content;
        const docname = meta.dataset.docname;
        const link = document.createElement("a");
        const root = window.DOCUMENTATION_OPTIONS?.URL_ROOT || "";
        link.href = docname ? `${root}${docname}.html#${id}` : `#${id}`;
        link.textContent = id;
        group.appendChild(link);
      });
      provenance.appendChild(group);
    }

    const findings = answer.querySelector("h3");
    if (findings) {
      findings.insertAdjacentElement("beforebegin", provenance);
    } else {
      answer.appendChild(provenance);
    }
  }

  function findingTable() {
    const heading = Array.from(document.querySelectorAll("h3")).find(
      (item) => item.firstChild?.textContent?.trim() === "Capability findings",
    );
    return heading?.closest("section")?.querySelector("table") || null;
  }

  function enhanceFindings() {
    const table = findingTable();
    if (!table) {
      return;
    }
    table.classList.add("exp-findings-table");
    const sections = Array.from(document.querySelectorAll("article h2")).filter((section) =>
      /^\d+\.\s/.test(section.firstChild?.textContent?.trim() || ""),
    );
    table.querySelectorAll("tbody tr").forEach((row) => {
      const cells = row.querySelectorAll("td");
      if (cells.length < 2) {
        return;
      }
      const capability = cells[0].textContent.trim();
      const outcome = cells[1].textContent.trim().toLowerCase();
      cells[1].classList.add("exp-outcome");
      if (outcome === "observed working") {
        cells[1].classList.add("exp-outcome-working");
      } else if (outcome === "working with caveat") {
        cells[1].classList.add("exp-outcome-caveat");
      } else if (outcome === "observed unsupported") {
        cells[1].classList.add("exp-outcome-unsupported");
      } else if (outcome === "inconclusive") {
        cells[1].classList.add("exp-outcome-inconclusive");
      }

      const target = sections.find((section) => {
        const title = (section.firstChild?.textContent || "")
          .replace(/^\d+\.\s*/, "")
          .trim();
        return title === capability;
      });
      if (!target) {
        return;
      }
      row.classList.add("exp-finding-link");
      row.tabIndex = 0;
      row.setAttribute("role", "link");
      row.setAttribute("aria-label", `Open evidence for ${capability}`);
      const openTarget = () => target.scrollIntoView({ behavior: "smooth", block: "start" });
      row.addEventListener("click", openTarget);
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openTarget();
        }
      });
    });
  }

  function enhanceExperiments() {
    moveAnswerNearQuestion();
    renderProvenance();
    enhanceFindings();
    document.querySelectorAll(".cell.tag_exp-evidence").forEach(enhanceEvidence);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceExperiments);
  } else {
    enhanceExperiments();
  }
})();
