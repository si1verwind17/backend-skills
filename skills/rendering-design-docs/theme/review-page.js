// design-review page behaviour: tabs, hash routing, links between ids, the outline of the open tab, diagrams fitted to
// the column with a full-size viewer, wide tables scrolled on their own. Inline it verbatim at the end of <body>.
// Contract: tabs are <a class="tab" data-tab="KEY" href="#KEY">; panels are <section class="panel" data-tab="KEY">
// with no id; <body data-gate="KEY"> names the gate tab; every defined id is an element with id="ID" inside its panel;
// diagrams are <figure class="diagram"> holding one <svg>.
(function () {
  document.documentElement.classList.add("js");
  var slice = function (list) { return Array.prototype.slice.call(list); };
  var tabs = slice(document.querySelectorAll(".tab[data-tab]"));
  var panels = slice(document.querySelectorAll(".panel[data-tab]"));
  var gate = document.body.getAttribute("data-gate") || (panels[0] && panels[0].getAttribute("data-tab"));
  var rail = document.querySelector("nav.tabs");
  var current = null;
  function panelOf(key) {
    for (var i = 0; i < panels.length; i++) if (panels[i].getAttribute("data-tab") === key) return panels[i];
    return null;
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  // Outline: the open tab's headings under the step rail; h4s show only under the h3 being read.
  var toc = el("div", "toc"), tocLinks = [], spy = null;
  if (rail) rail.appendChild(toc);
  function buildToc(panel) {
    toc.innerHTML = "";
    tocLinks = [];
    if (spy) spy.disconnect();
    var heads = slice(panel.querySelectorAll(".owed > h2, .doc h2, .doc h3, .doc h4"));
    if (heads.length < 2) return;
    toc.appendChild(el("p", "toc-title", "On this page"));
    var list = el("ul"), parent = null, key = panel.getAttribute("data-tab");
    heads.forEach(function (h, i) {
      if (!h.id) h.id = "s-" + key + "-" + (i + 1);
      var level = h.tagName === "H4" ? 3 : h.tagName === "H3" ? 2 : 1;
      var li = el("li", "l" + level), a = el("a", null, h.textContent.trim());
      a.href = "#" + h.id;
      li.appendChild(a);
      list.appendChild(li);
      if (level === 2) parent = li;
      if (level === 1) parent = null;
      li.tocParent = level === 3 ? parent : null;
      if (level === 3 && parent) parent.classList.add("has-sub");
      a.tocHead = h;
      tocLinks.push(a);
    });
    toc.appendChild(list);
    if (!("IntersectionObserver" in window)) return;
    spy = new IntersectionObserver(markReading, { rootMargin: "0px 0px -70% 0px" });
    heads.forEach(function (h) { spy.observe(h); });
    markReading();
  }
  // The heading being read is the last one whose top has passed the upper third of the viewport.
  function markReading() {
    var at = null, limit = window.innerHeight * 0.3;
    tocLinks.forEach(function (a) { if (a.tocHead.getBoundingClientRect().top <= limit) at = a; });
    if (!at) at = tocLinks[0];
    var li = at && at.parentNode, open = li && (li.tocParent || (li.classList.contains("has-sub") ? li : null));
    tocLinks.forEach(function (a) {
      var item = a.parentNode;
      if (a === at) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
      item.classList.toggle("open", item === open || item.tocParent === open);
    });
  }

  // Wide tables scroll inside their own box, so the others keep a sticky header row.
  function wrapWideTables(panel) {
    slice(panel.querySelectorAll(".doc table")).forEach(function (t) {
      if (t.parentNode.classList.contains("table-scroll") || t.scrollWidth <= t.parentNode.clientWidth + 1) return;
      var box = el("div", "table-scroll");
      t.parentNode.insertBefore(box, t);
      box.appendChild(t);
    });
  }

  // Diagrams fit the column; the bar says at what scale and opens the full-size viewer.
  function naturalSize(svg) {
    var vb = svg.viewBox && svg.viewBox.baseVal;
    if (vb && vb.width) return { w: vb.width, h: vb.height };
    return { w: parseFloat(svg.getAttribute("width")) || svg.getBoundingClientRect().width,
      h: parseFloat(svg.getAttribute("height")) || svg.getBoundingClientRect().height };
  }
  function diagramTitle(fig) {
    for (var e = fig.previousElementSibling; e; e = e.previousElementSibling) {
      if (/^H[1-6]$/.test(e.tagName)) return e.textContent.trim();
      var only = e.tagName === "P" && e.children.length === 1 && e.firstElementChild.tagName === "STRONG";
      if (only && e.textContent.trim() === e.firstElementChild.textContent.trim()) return e.textContent.trim();
    }
    return "Diagram";
  }
  slice(document.querySelectorAll("figure.diagram")).forEach(function (fig) {
    var bar = el("div", "diagram-bar"), scale = el("span", "diagram-scale"), open = el("button", "diagram-open", "Open full size");
    open.type = "button";
    open.addEventListener("click", function () { openViewer(fig, open); });
    fig.addEventListener("click", function (ev) {
      if (fig.classList.contains("scaled") && ev.target.closest("svg")) openViewer(fig, open);
    });
    bar.appendChild(scale);
    bar.appendChild(open);
    fig.appendChild(bar);
  });
  function measureDiagrams(panel) {
    slice(panel.querySelectorAll("figure.diagram")).forEach(function (fig) {
      var svg = fig.querySelector(":scope > svg"), scale = fig.querySelector(".diagram-scale");
      if (!svg || !scale) return;
      var shown = svg.getBoundingClientRect().width, ratio = shown / naturalSize(svg).w;
      var scaled = shown > 0 && ratio < 0.98;
      fig.classList.toggle("scaled", scaled);
      scale.textContent = scaled ? "Shown at " + Math.round(ratio * 100) + "% · click to open full size" : "";
    });
  }

  var viewer = el("div", "viewer"), vTitle = el("p", "viewer-title"), vStage = el("div", "viewer-stage"), vPct = el("output", "viewer-pct");
  var vBar = el("div", "viewer-bar"), vFig = null, vSvg = null, vNext = null, vOpener = null, zoom = 1, size = null;
  viewer.hidden = true;
  viewer.setAttribute("role", "dialog");
  viewer.setAttribute("aria-modal", "true");
  vTitle.id = "viewer-title";
  viewer.setAttribute("aria-labelledby", vTitle.id);
  vStage.tabIndex = 0;
  vBar.appendChild(vTitle);
  [["out", "−", "Zoom out"], ["pct"], ["in", "+", "Zoom in"], ["fit", "Fit", "Fit to screen"], ["one", "1:1", "Actual size"],
    ["close", "Close ✕", "Close"]].forEach(function (b) {
    if (b[0] === "pct") { vBar.appendChild(vPct); return; }
    var btn = el("button", "viewer-" + b[0], b[1]);
    btn.type = "button";
    btn.setAttribute("aria-label", b[2]);
    btn.setAttribute("data-act", b[0]);
    vBar.appendChild(btn);
  });
  vBar.appendChild(el("span", "viewer-hint", "Drag to pan · Ctrl + wheel to zoom · Esc to close"));
  viewer.appendChild(vBar);
  viewer.appendChild(vStage);
  document.body.appendChild(viewer);

  function fitZoom() {
    return Math.min(1, (vStage.clientWidth - 48) / size.w, (vStage.clientHeight - 48) / size.h);
  }
  // Keeps the stage point (cx, cy) still while the scale changes.
  function setZoom(z, cx, cy) {
    z = Math.max(0.05, Math.min(4, z));
    if (cx === undefined) { cx = vStage.clientWidth / 2; cy = vStage.clientHeight / 2; }
    var px = (vStage.scrollLeft + cx) / zoom, py = (vStage.scrollTop + cy) / zoom;
    zoom = z;
    vSvg.style.width = size.w * z + "px";
    vSvg.style.height = size.h * z + "px";
    vStage.scrollLeft = px * z - cx;
    vStage.scrollTop = py * z - cy;
    vPct.textContent = Math.round(z * 100) + "%";
  }
  function openViewer(fig, opener) {
    var svg = fig.querySelector(":scope > svg");
    if (!svg || vSvg) return;
    vFig = fig; vSvg = svg; vNext = svg.nextSibling; vOpener = opener; size = naturalSize(svg);
    fig.style.minHeight = fig.offsetHeight + "px";
    vTitle.textContent = diagramTitle(fig);
    vStage.appendChild(svg);
    viewer.hidden = false;
    document.documentElement.classList.add("viewing");
    zoom = 1;
    setZoom(1, 0, 0);
    vStage.scrollLeft = 0;
    vStage.scrollTop = 0;
    vStage.focus();
  }
  function closeViewer() {
    if (!vSvg) return;
    vSvg.style.width = vSvg.style.height = "";
    vFig.insertBefore(vSvg, vNext);
    vFig.style.minHeight = "";
    viewer.hidden = true;
    document.documentElement.classList.remove("viewing");
    vSvg = null;
    if (vOpener) vOpener.focus();
  }
  vBar.addEventListener("click", function (ev) {
    var act = ev.target.getAttribute && ev.target.getAttribute("data-act");
    if (act === "close") closeViewer();
    else if (act === "in") setZoom(zoom * 1.25);
    else if (act === "out") setZoom(zoom / 1.25);
    else if (act === "fit") setZoom(fitZoom());
    else if (act === "one") setZoom(1);
  });
  viewer.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") closeViewer();
    else if (ev.key === "+" || ev.key === "=") setZoom(zoom * 1.25);
    else if (ev.key === "-") setZoom(zoom / 1.25);
    else if (ev.key === "0") setZoom(fitZoom());
    else if (ev.key === "1") setZoom(1);
    else if (ev.key === "Tab") {
      var stops = slice(viewer.querySelectorAll("button")).concat([vStage]);
      var i = stops.indexOf(document.activeElement), next = ev.shiftKey ? i - 1 : i + 1;
      stops[(next + stops.length) % stops.length].focus();
    } else return;
    ev.preventDefault();
  });
  vStage.addEventListener("wheel", function (ev) {
    if (!ev.ctrlKey && !ev.metaKey) return;
    ev.preventDefault();
    var r = vStage.getBoundingClientRect();
    setZoom(zoom * Math.exp(-ev.deltaY * 0.002), ev.clientX - r.left, ev.clientY - r.top);
  }, { passive: false });
  var drag = null;
  vStage.addEventListener("pointerdown", function (ev) {
    if (ev.button !== 0) return;
    drag = { x: ev.clientX, y: ev.clientY, l: vStage.scrollLeft, t: vStage.scrollTop };
    vStage.setPointerCapture(ev.pointerId);
    vStage.classList.add("dragging");
  });
  vStage.addEventListener("pointermove", function (ev) {
    if (!drag) return;
    vStage.scrollLeft = drag.l - (ev.clientX - drag.x);
    vStage.scrollTop = drag.t - (ev.clientY - drag.y);
  });
  function endDrag() { drag = null; vStage.classList.remove("dragging"); }
  vStage.addEventListener("pointerup", endDrag);
  vStage.addEventListener("pointercancel", endDrag);

  // Layout-dependent work runs when a panel is first visible, and again on resize.
  function lay(panel) {
    wrapWideTables(panel);
    measureDiagrams(panel);
  }
  function show(key) {
    if (!panelOf(key)) key = gate;
    panels.forEach(function (p) { p.hidden = p.getAttribute("data-tab") !== key; });
    tabs.forEach(function (t) {
      if (t.getAttribute("data-tab") === key) t.setAttribute("aria-current", "page");
      else t.removeAttribute("aria-current");
    });
    var changed = key !== current;
    current = key;
    if (changed) {
      lay(panelOf(key));
      buildToc(panelOf(key));
    }
    return changed;
  }
  // A new tab starts at its top: if the reader is scrolled past it, bring the panel's top into view.
  function toPanelTop() {
    var panel = panelOf(current);
    if (!panel) return;
    var top = panel.getBoundingClientRect().top + window.pageYOffset - 24;
    if (window.pageYOffset > top) window.scrollTo(0, top);
  }
  function route() {
    closeViewer();
    var hash = decodeURIComponent(location.hash.slice(1));
    if (!hash) { if (show(gate)) toPanelTop(); return; }
    if (panelOf(hash)) { if (show(hash)) toPanelTop(); return; }
    var target = document.getElementById(hash);
    var panel = target && target.closest(".panel[data-tab]");
    show(panel ? panel.getAttribute("data-tab") : gate);
    if (!target) return;
    for (var d = target.closest("details"); d; d = d.parentElement && d.parentElement.closest("details")) d.open = true;
    target.scrollIntoView({ block: "start" });
  }
  var resizing = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizing);
    resizing = setTimeout(function () { if (panelOf(current)) lay(panelOf(current)); }, 150);
  });
  window.addEventListener("hashchange", route);
  route();
})();
