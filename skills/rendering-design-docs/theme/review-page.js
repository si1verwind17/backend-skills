// design-review page behaviour: tabs, hash routing, links between ids. Inline it verbatim at the end of <body>.
// Contract: tabs are <a class="tab" data-tab="KEY" href="#KEY">; panels are <section class="panel" data-tab="KEY">
// with no id; <body data-gate="KEY"> names the gate tab; every defined id is an element with id="ID" inside its panel.
(function () {
  document.documentElement.classList.add("js");
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab[data-tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll(".panel[data-tab]"));
  var gate = document.body.getAttribute("data-gate") || (panels[0] && panels[0].getAttribute("data-tab"));
  var current = null;
  function panelOf(key) {
    for (var i = 0; i < panels.length; i++) if (panels[i].getAttribute("data-tab") === key) return panels[i];
    return null;
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
  window.addEventListener("hashchange", route);
  route();
})();
