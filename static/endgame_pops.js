(() => {
  const holder = document.querySelector("#pop-holder");
  const inventory = document.querySelector("#pop-inventory");
  const readiness = document.querySelector("#pop-readiness");
  const componentCount = document.querySelector("#pop-component-count");
  const readyCount = document.querySelector("#pop-ready-count");
  if (!holder || !inventory || !readiness || !componentCount || !readyCount) return;

  const items = Array.isArray(window.POP_ITEMS) ? window.POP_ITEMS : [];
  const targets = Array.isArray(window.POP_TARGETS) ? window.POP_TARGETS : [];
  let area = "Sky";
  let saved = {};
  const text = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[character]));
  const amount = (name, key) => Number(saved[name]?.[key] || 0);
  const totals = () => Object.keys(saved).reduce((result, name) => {
    Object.entries(saved[name]).forEach(([key, value]) => { result[key] = (result[key] || 0) + Number(value); });
    return result;
  }, {});

  const render = () => {
    const aggregate = totals();
    const areaItems = items.filter(item => item.area === area);
    inventory.innerHTML = areaItems.map(item => {
      const owners = Object.keys(saved).filter(name => amount(name, item.key) > 0);
      return `<article class="pop-item"><div><b>${text(item.name)}</b><small>${text(item.source)}${item.bundle ? ` · ${item.bundle} required per pop` : ""}</small></div><div class="quantity-stepper"><button type="button" data-pop-change="-1" data-key="${text(item.key)}" aria-label="Remove ${text(item.name)}">−</button><b>${amount(holder.value, item.key)}</b><button type="button" data-pop-change="1" data-key="${text(item.key)}" aria-label="Add ${text(item.name)}">+</button></div><span class="holder-list">Linkshell total: <b>${aggregate[item.key] || 0}</b>${owners.length ? ` · Held by ${owners.map(text).join(", ")}` : " · No recorded holders"}</span></article>`;
    }).join("") || "<p class=\"event-empty\">No components are configured for this area.</p>";

    let ready = 0;
    readiness.innerHTML = targets.filter(target => target.area === area).map(target => {
      const requirements = target.requires.map(raw => {
        const [key, needed] = raw.split(":");
        const item = items.find(entry => entry.key === key);
        const required = Number(needed || 1);
        const held = aggregate[key] || 0;
        return {item, required, held, met: held >= required};
      });
      const complete = requirements.every(requirement => requirement.met);
      if (complete) ready += 1;
      const sets = Math.min(...requirements.map(requirement => Math.floor(requirement.held / requirement.required)));
      return `<article class="pop-target ${complete ? "ready" : "partial"}"><header><h4>${text(target.name)}</h4><span class="readiness-badge">${complete ? `${sets} pop${sets === 1 ? "" : "s"} ready` : "Components needed"}</span></header><div class="requirement-list">${requirements.map(requirement => `<span class="${requirement.met ? "have" : ""}">${text(requirement.item?.name || requirement.item)} ${requirement.held}/${requirement.required}</span>`).join("")}</div></article>`;
    }).join("") || "<p class=\"event-empty\">No encounters are configured for this area.</p>";
    componentCount.textContent = `${areaItems.reduce((sum, item) => sum + (aggregate[item.key] || 0), 0)} components held`;
    readyCount.textContent = `${ready} ready`;
  };

  document.querySelectorAll("[data-pop-area]").forEach(button => button.addEventListener("click", () => {
    area = button.dataset.popArea;
    document.querySelectorAll("[data-pop-area]").forEach(candidate => candidate.classList.toggle("active", candidate === button));
    render();
  }));
  holder.addEventListener("change", render);
  inventory.addEventListener("click", async event => {
    const button = event.target.closest("[data-pop-change]");
    if (!button) return;
    button.disabled = true;
    try {
      const response = await fetch("/api/endgame/pops", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRF-Token": window.ENDGAME_CSRF},
        body: JSON.stringify({holder: holder.value, item_key: button.dataset.key, delta: Number(button.dataset.popChange)}),
      });
      if (!response.ok) throw new Error("Could not save the pop inventory update.");
      saved = (await response.json()).inventory || {};
      render();
    } catch (error) { alert(error.message); button.disabled = false; }
  });
  render();
  fetch("/api/endgame/pops", {headers: {Accept: "application/json"}})
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(payload => { saved = payload.inventory || {}; render(); })
    .catch(() => render());
})();
