(() => {
  const data = window.GEAR_OPTIMIZER;
  if (!data) return;

  let bestSet = {};
  const jobControl = document.querySelector("#gear-job");
  const levelControl = document.querySelector("#gear-level");
  const primaryControl = document.querySelector("#gear-primary-stat");
  const secondaryControl = document.querySelector("#gear-secondary-stat");
  const negativeControl = document.querySelector("#gear-negative");
  const raceControl = document.querySelector("#gear-race");
  let catalog = [];
  const slotOrder = ["main", "sub", "ranged", "ammo", "head", "body", "hands", "legs", "feet", "neck", "waist", "ear1", "ear2", "ring1", "ring2", "back"];
  const labels = { main: "Main", sub: "Sub", ranged: "Ranged", ammo: "Ammo", head: "Head", body: "Body", hands: "Hands", legs: "Legs", feet: "Feet", neck: "Neck", waist: "Waist", ear1: "Left Ear", ear2: "Right Ear", ring1: "Left Ring", ring2: "Right Ring", back: "Back" };

  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const itemStats = item => item && item.stats ? item.stats : {};
  const selectedStats = () => [primaryControl.value, secondaryControl.value].filter(Boolean);
  const score = item => {
    const stats = itemStats(item);
    const direction = negativeControl.checked ? -1 : 1;
    return (Number(stats[primaryControl.value] || 0) * 2 + Number(stats[secondaryControl.value] || 0)) * direction;
  };

  const applicableSlots = item => {
    if (Array.isArray(item.slots)) {
      return [...new Set(item.slots.flatMap(slot => applicableSlots({ slot })))];
    }
    const slot = String(item.slot || "").toLowerCase();
    if (slot.includes("main/sub")) return ["main", "sub"];
    if (slot === "range" || slot === "ranged") return ["ranged"];
    if (slot === "ear") return ["ear1", "ear2"];
    if (slot === "ring") return ["ring1", "ring2"];
    const match = slotOrder.find(candidate => candidate.replace(/[12]$/, "") === slot);
    return match ? [match] : [];
  };

  const isCompatible = item => {
    const level = Number(levelControl.value || 75);
    const jobs = Array.isArray(item.jobs) ? item.jobs : String(item.jobs || "").split("/");
    const races = Array.isArray(item.races) ? item.races : [];
    return Number(item.level || 0) <= level &&
      (!jobs.length || jobs.includes("All Jobs") || jobs.includes(jobControl.value)) &&
      (!races.length || !raceControl.value || races.includes(raceControl.value));
  };

  const renderBestSet = () => {
    const container = document.querySelector("#gear-best-slots");
    let equippedCount = 0;
    const cards = slotOrder.map(slot => {
      const item = bestSet[slot];
      const card = element("article", `gear-slot${item ? "" : " empty"}`);
      card.append(element("span", "gear-slot-label", labels[slot]));
      if (!item) {
        card.append(element("strong", "", "No matching item"));
        return card;
      }
      equippedCount += 1;
      card.append(
        element("strong", "", item.name),
        element("span", "gear-item-level", `Lv. ${item.level || 0} | ${item.slot || labels[slot]}`),
        element("p", "gear-description", item.description || "No description"),
      );
      return card;
    });
    container.replaceChildren(...cards);
    document.querySelector("#gear-load-summary").textContent = `${equippedCount}/${slotOrder.length} slots filled`;
  };

  const renderTotals = () => {
    const totals = {};
    Object.values(bestSet).filter(Boolean).forEach(item => {
      Object.entries(itemStats(item)).forEach(([name, value]) => {
        totals[name] = (totals[name] || 0) + Number(value);
      });
    });
    const priorities = new Set(selectedStats());
    const nodes = Object.entries(totals).sort(([a], [b]) => a.localeCompare(b)).map(([name, value]) => {
      const chip = element("span", `gear-stat${priorities.has(name) ? " priority" : ""}`);
      chip.append(document.createTextNode(name), element("strong", "", `${value >= 0 ? "+" : ""}${value}`));
      return chip;
    });
    document.querySelector("#gear-stat-totals").replaceChildren(...(nodes.length ? nodes : [element("span", "gear-empty", "No equipment stats available.")]));
  };

  const currentComparison = item => {
    const slots = applicableSlots(item);
    if (!slots.length) return null;
    return slots.map(slot => ({ slot, current: bestSet[slot], delta: score(item) - score(bestSet[slot]) }))
      .sort((a, b) => b.delta - a.delta)[0];
  };

  const renderCatalog = () => {
    const stat = primaryControl.value;
    document.querySelector("#catalog-stat-name").textContent = stat;
    const matches = catalog.filter(item => {
      const value = Number(itemStats(item)[stat] || 0);
      return isCompatible(item) && (negativeControl.checked ? value < 0 : value > 0);
    });
    const groups = new Map();
    matches.forEach(item => (item.slots || []).forEach(slot => {
      if (!groups.has(slot)) groups.set(slot, []);
      groups.get(slot).push(item);
    }));
    const orderedSlots = ["Main", "Sub", "Ranged", "Ammo", "Head", "Body", "Hands", "Legs", "Feet", "Neck", "Waist", "Ear", "Ring", "Back"];
    const sections = orderedSlots.filter(slot => groups.has(slot)).map(slot => {
      const direction = negativeControl.checked ? -1 : 1;
      const items = groups.get(slot).sort((a, b) =>
        (Number(itemStats(b)[stat] || 0) - Number(itemStats(a)[stat] || 0)) * direction ||
        a.level - b.level || a.name.localeCompare(b.name)
      );
      const section = element("section", "gear-catalog-slot");
      const header = document.createElement("header");
      header.append(element("h3", "", slot), element("span", "", `${items.length} items`));
      const list = element("div", "gear-catalog-items");
      list.replaceChildren(...items.map(item => {
        const comparison = currentComparison(item);
        const currentValue = comparison && comparison.current ? Number(itemStats(comparison.current)[stat] || 0) : 0;
        const value = Number(itemStats(item)[stat] || 0);
        const delta = value - currentValue;
        const row = element("article", "gear-catalog-item");
        const improvement = delta * direction;
        row.append(
          element("h4", "", item.name),
          element("strong", "gear-catalog-value", `${value >= 0 ? "+" : ""}${value}`),
          element("strong", `gear-catalog-delta${improvement < 0 ? " negative" : ""}`, `${delta >= 0 ? "+" : ""}${delta}`),
          element("p", "", `Lv. ${item.level} | ${item.description || stat}`),
        );
        return row;
      }));
      section.append(header, list);
      return section;
    });
    document.querySelector("#gear-catalog-count").textContent = `${matches.length} compatible items`;
    document.querySelector("#gear-catalog-results").replaceChildren(...(sections.length ? sections : [element("p", "gear-empty", `No compatible ${stat} equipment found.`)]));
  };

  const refresh = () => {
    const stat = primaryControl.value;
    const direction = negativeControl.checked ? -1 : 1;
    const candidates = catalog.filter(item => {
      const value = Number(itemStats(item)[stat] || 0);
      return isCompatible(item) && (negativeControl.checked ? value < 0 : value > 0);
    }).sort((a, b) => (score(b) - score(a)) || a.level - b.level || a.name.localeCompare(b.name));
    bestSet = {};
    slotOrder.forEach(slot => {
      bestSet[slot] = candidates.find(item => applicableSlots(item).includes(slot)) || null;
    });
    renderBestSet();
    renderTotals();
    renderCatalog();
  };

  jobControl.addEventListener("change", refresh);
  [levelControl, raceControl, primaryControl, secondaryControl, negativeControl].forEach(control => control.addEventListener("change", refresh));
  refresh();
  fetch(data.catalogUrl)
    .then(response => {
      if (!response.ok) throw new Error("Equipment catalog unavailable");
      return response.json();
    })
    .then(payload => {
      catalog = payload.rows || [];
      (payload.stats || []).forEach(stat => {
        [primaryControl, secondaryControl].forEach(control => {
          if (![...control.options].some(option => option.value === stat)) {
            control.add(new Option(stat, stat));
          }
        });
      });
      refresh();
    })
    .catch(error => {
      document.querySelector("#gear-catalog-count").textContent = error.message;
    });
})();
