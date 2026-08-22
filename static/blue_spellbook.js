(() => {
  const levelInput = document.querySelector("#book-level");
  if (!levelInput) return;
  const learned = new Set(window.LEARNED_BLUE_SPELLS || []);
  const equipped = new Set((window.BLUE_TEMPLATE && window.BLUE_TEMPLATE.spells) || []);
  let spells = [];
  const el = id => document.querySelector(`#${id}`);
  const rightRail = document.createElement("aside");
  rightRail.className = "spellbook-right-rail";
  document.querySelector(".spellbook-three-column").append(rightRail);
  rightRail.append(document.querySelector(".build-settings"), document.querySelector(".template-library"));
  const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
  const pointLimit = level => 10 + Math.floor((level - 1) / 10) * 5;
  const slotLimit = level => Math.min(20, 6 + Math.floor((level - 1) / 10) * 2);
  const level = () => Math.min(75, Math.max(1, Number(levelInput.value) || 75));
  const contribution = spell => !spell.trait ? 0 : spell.trait === "Auto Refresh" ? Number(spell.trait_weight || 0) : Number(spell.trait_weight || 0) * 4;
  const selectedValues = container => [...container.querySelectorAll("input:checked")].map(input => input.value);
  const parseStats = spell => (spell.set_stats || []).flatMap(text => {
    const match = String(text).replace(/,$/, "").match(/^(.+?)([+-]\d+)$/);
    return match ? [{ name: match[1].trim(), value: Number(match[2]) }] : [];
  });
  const totals = list => {
    const result = {};
    list.forEach(spell => parseStats(spell).forEach(stat => { result[stat.name] = (result[stat.name] || 0) + stat.value; }));
    return result;
  };
  const current = () => spells.filter(spell => equipped.has(spell.spell));
  const cost = list => list.reduce((sum, spell) => sum + Number(spell.set_points || 0), 0);
  const canAdd = spell => {
    const list = current();
    return spell.spell_level <= level() && list.length < slotLimit(level()) && cost(list) + Number(spell.set_points || 0) <= pointLimit(level());
  };
  const syncForm = () => {
    el("template-level").value = level();
    el("template-spells").replaceChildren(...[...equipped].map(name => {
      const input = document.createElement("input"); input.type = "hidden"; input.name = "spells"; input.value = name; return input;
    }));
  };
  const badge = spell => `<span class="ownership ${learned.has(spell.spell) ? "known" : "missing"}">${learned.has(spell.spell) ? "Learned" : "Need to learn"}</span>`;
  const effectTooltip = spell => spell.description ? `<span class="spell-effect-tip" tabindex="0"><span class="spell-effect-name">${escapeHtml(spell.spell)}</span><span class="spell-effect-popover" role="tooltip">${escapeHtml(spell.description)}</span></span>` : `<span class="spell-effect-name">${escapeHtml(spell.spell)}</span>`;
  const effectsSection = document.createElement("section");
  effectsSection.className = "active-effects-summary";
  effectsSection.innerHTML = '<h3>Additional Effect / Spell Equivalent</h3><p class="effect-summary-help">Effects granted by the equipped spells are listed with their familiar WHM, RDM, or BLM equivalent where applicable.</p><div id="active-effects"></div>';
  document.querySelector(".build-summary").append(effectsSection);
  const quickMatches = () => {
    const query = el("quick-spell-search").value.trim().toLowerCase();
    return spells.filter(spell => spell.spell_level <= level() && !equipped.has(spell.spell) && (!query || `${spell.spell} ${spell.trait || ""} ${(spell.set_stats || []).join(" ")}`.toLowerCase().includes(query)));
  };
  const renderQuickPicker = () => {
    el("quick-spell-results").innerHTML = quickMatches().map(spell => `<article><div><strong>${effectTooltip(spell)}</strong>${badge(spell)}<small>Lv. ${spell.spell_level} · ${spell.set_points} points · ${spell.trait || "No trait"}</small></div><button class="button" type="button" data-quick-add="${spell.spell}" ${canAdd(spell) ? "" : "disabled"}>Add</button></article>`).join("") || '<p class="book-empty">No available spells match.</p>';
  };
  const openPicker = () => { el("quick-spell-search").value = ""; renderQuickPicker(); el("spell-picker-modal").hidden = false; el("quick-spell-search").focus(); };
  const showSpell = spell => {
    el("spell-detail-title").textContent = spell.spell;
    const typeLabel = spell.spell_type === "Magical" && spell.element
      ? `Magical (${spell.element})`
      : (spell.spell_type || "Support");
    el("spell-detail-content").innerHTML = `<div class="spell-detail-grid"><div><span>Blue Mage level</span><strong>${spell.spell_level}</strong></div><div><span>Set cost</span><strong>${spell.set_points} points</strong></div><div><span>Type</span><strong>${typeLabel}</strong></div><div><span>Status</span><strong>${learned.has(spell.spell) ? "Learned" : "Need to learn"}</strong></div><div><span>Trait contribution</span><strong>${spell.trait ? `${spell.trait} +${contribution(spell)}` : "None"}</strong></div><div><span>Set stats</span><strong>${(spell.set_stats || []).join(" · ") || "None"}</strong></div></div>`;
    el("spell-detail-modal").hidden = false;
  };
  const render = () => {
    const lvl = level();
    const active = current().filter(spell => spell.spell_level <= lvl);
    [...equipped].forEach(name => { const spell = spells.find(row => row.spell === name); if (!spell || spell.spell_level > lvl) equipped.delete(name); });
    const used = cost(active);
    el("spell-count").textContent = active.length;
    el("book-points").textContent = `${used} / ${pointLimit(lvl)}`;
    el("book-slots").textContent = `${active.length} / ${slotLimit(lvl)}`;
    el("book-points").classList.toggle("over", used > pointLimit(lvl));
    el("active-spells").innerHTML = `${active.map(spell => `<article class="equipped-spell" data-view-spell="${spell.spell}" tabindex="0"><button type="button" data-remove="${spell.spell}" aria-label="Remove ${spell.spell}">×</button><div><strong>${effectTooltip(spell)}</strong>${badge(spell)}</div><span>Lv. ${spell.spell_level} · ${spell.set_points} pts</span><small>${spell.trait ? `${spell.trait} +${contribution(spell)}` : "No trait"} · ${(spell.set_stats || []).join(", ") || "No set stats"}</small></article>`).join("")}<button class="add-spell-tile" id="add-spell-tile" type="button"><b>+</b><span>Add Spell</span><small>${active.length}/${slotLimit(lvl)} slots used</small></button>`;
    const traitPoints = {};
    active.forEach(spell => { if (spell.trait) traitPoints[spell.trait] = (traitPoints[spell.trait] || 0) + contribution(spell); });
    const traitEntries = Object.entries(traitPoints).sort();
    el("active-traits").innerHTML = traitEntries.length ? traitEntries.map(([name, points]) => `<span class="summary-chip ${points >= 8 ? "active" : "partial"}"><b>${name}${points >= 8 ? ` Tier ${Math.floor(points / 8)}` : ""}</b><small>${points}/8 trait points${points < 8 ? " · inactive" : ""}</small></span>`).join("") : '<p class="book-empty">No trait contributions yet.</p>';
    const statEntries = Object.entries(totals(active)).filter(([, value]) => value).sort();
    el("active-stats").innerHTML = statEntries.length ? statEntries.map(([name, value]) => `<span class="summary-chip active"><b>${name} ${value > 0 ? "+" : ""}${value}</b></span>`).join("") : '<p class="book-empty">No set stat bonuses yet.</p>';
    const activeEffects = {};
    active.forEach(spell => (spell.effects || []).forEach(effect => { (activeEffects[effect] ||= []).push(spell.spell); }));
    const effectEntries = Object.entries(activeEffects).sort(([a], [b]) => a.localeCompare(b));
    const equivalentNames = { "HP Drain": "Drain", "MP Drain": "Aspir", "Defense Down": "Dia", "Attack Down": "Bio", "Cure": "Cure" };
    el("active-effects").innerHTML = effectEntries.length ? effectEntries.map(([effect, names]) => `<span class="summary-chip effect"><b>${escapeHtml(effect)}${equivalentNames[effect] ? ` (${equivalentNames[effect]})` : ""}</b><small>${names.map(escapeHtml).join(" · ")}</small></span>`).join("") : '<p class="book-empty">No additional effects are provided by the currently equipped spells.</p>';
    const query = el("book-search").value.trim().toLowerCase();
    const visible = spells.filter(spell => spell.spell_level <= lvl && (!el("book-learned-only").checked || learned.has(spell.spell)) && (!query || `${spell.spell} ${spell.trait || ""} ${(spell.effects || []).join(" ")} ${(spell.set_stats || []).join(" ")}`.toLowerCase().includes(query)));
    el("catalog-count").textContent = `${visible.length} spells`;
    el("book-catalog").innerHTML = visible.map(spell => `<article class="${equipped.has(spell.spell) ? "selected" : ""}"><div><strong>${effectTooltip(spell)}</strong>${badge(spell)}<small>Lv. ${spell.spell_level} · ${spell.set_points} points</small></div><div><span>${spell.trait ? `${spell.trait} +${contribution(spell)}` : "No trait"}</span><small>${(spell.set_stats || []).join(" · ") || "No set stats"}</small></div><button class="button" type="button" data-toggle="${spell.spell}" ${!equipped.has(spell.spell) && !canAdd(spell) ? "disabled" : ""}>${equipped.has(spell.spell) ? "Remove" : "Add"}</button></article>`).join("");
    syncForm();
  };
  const cheapestTraitSet = (trait, pool, maxPoints, maxSlots) => {
    const candidates = pool.filter(spell => spell.trait === trait).sort((a, b) => a.set_points - b.set_points);
    let best = null;
    const visit = (index, chosen, points, spent) => {
      if (points >= 8) { if (!best || spent < best.spent || (spent === best.spent && chosen.length < best.spells.length)) best = { spells: [...chosen], spent }; return; }
      if (index >= candidates.length || chosen.length >= maxSlots || (best && spent >= best.spent)) return;
      for (let i = index; i < candidates.length; i += 1) {
        const next = candidates[i];
        if (spent + next.set_points <= maxPoints) visit(i + 1, [...chosen, next], points + contribution(next), spent + next.set_points);
      }
    };
    visit(0, [], 0, 0); return best && best.spells;
  };
  const solve = () => {
    const wantedTraits = selectedValues(el("goal-traits"));
    const wantedEffects = selectedValues(el("goal-effects"));
    const wantedStats = selectedValues(el("goal-stats"));
    if (!wantedTraits.length && !wantedEffects.length && !wantedStats.length) { el("goal-result").textContent = "Select at least one trait, effect, or stat priority."; return; }
    const pool = spells.filter(spell => spell.spell_level <= level() && (!el("goal-learned-only").checked || learned.has(spell.spell)));
    const chosen = [];
    for (const effect of wantedEffects) {
      if (chosen.some(spell => (spell.effects || []).includes(effect))) continue;
      const option = pool.filter(spell => !chosen.includes(spell) && (spell.effects || []).includes(effect)).sort((a, b) => a.set_points - b.set_points || a.spell_level - b.spell_level)[0];
      if (!option || chosen.length >= slotLimit(level()) || cost(chosen) + option.set_points > pointLimit(level())) { el("goal-result").textContent = `No valid ${effect} spell fits the selected restrictions.`; return; }
      chosen.push(option);
    }
    for (const trait of wantedTraits) {
      const options = pool.filter(spell => !chosen.includes(spell));
      const combo = cheapestTraitSet(trait, options, pointLimit(level()) - cost(chosen), slotLimit(level()) - chosen.length);
      if (!combo) { el("goal-result").textContent = `No valid ${trait} combination fits the selected restrictions.`; return; }
      combo.forEach(spell => { if (!chosen.includes(spell)) chosen.push(spell); });
    }
    if (el("trait-priority").value === "max" && wantedTraits.length) {
      pool.filter(spell => wantedTraits.includes(spell.trait) && !chosen.includes(spell)).sort((a, b) => (contribution(b) / b.set_points) - (contribution(a) / a.set_points)).forEach(spell => {
        if (chosen.length < slotLimit(level()) && cost(chosen) + spell.set_points <= pointLimit(level())) chosen.push(spell);
      });
    }
    if (wantedStats.length) {
      pool.filter(spell => !chosen.includes(spell)).map(spell => ({ spell, value: parseStats(spell).filter(stat => wantedStats.includes(stat.name)).reduce((sum, stat) => sum + stat.value, 0) })).filter(row => row.value > 0).sort((a, b) => (b.value / b.spell.set_points) - (a.value / a.spell.set_points)).forEach(({ spell }) => { if (chosen.length < slotLimit(level()) && cost(chosen) + spell.set_points <= pointLimit(level())) chosen.push(spell); });
    }
    equipped.clear(); chosen.forEach(spell => equipped.add(spell.spell));
    const missing = chosen.filter(spell => !learned.has(spell.spell)).length;
    el("goal-result").textContent = `Applied ${chosen.length} spells for ${cost(chosen)} points${missing ? `; ${missing} still need to be learned` : "; all are learned"}.`;
    render();
  };
  document.addEventListener("click", event => {
    const toggle = event.target.closest("[data-toggle]"); const remove = event.target.closest("[data-remove]"); const quick = event.target.closest("[data-quick-add]"); const view = event.target.closest("[data-view-spell]");
    if (toggle) { const name = toggle.dataset.toggle; if (equipped.has(name)) equipped.delete(name); else { const spell = spells.find(row => row.spell === name); if (spell && canAdd(spell)) equipped.add(name); } render(); }
    if (remove) { event.stopPropagation(); equipped.delete(remove.dataset.remove); render(); }
    else if (view) { const spell = spells.find(row => row.spell === view.dataset.viewSpell); if (spell) showSpell(spell); }
    if (quick) { const spell = spells.find(row => row.spell === quick.dataset.quickAdd); if (spell && canAdd(spell)) { equipped.add(spell.spell); render(); renderQuickPicker(); } }
    if (event.target.closest("#add-spell-tile")) openPicker();
  });
  levelInput.addEventListener("input", render); el("book-search").addEventListener("input", render); el("book-learned-only").addEventListener("change", render);
  el("clear-book").addEventListener("click", () => { equipped.clear(); render(); }); el("solve-goals").addEventListener("click", solve);
  el("clear-goals").addEventListener("click", () => { document.querySelectorAll(".goal-options input").forEach(input => { input.checked = false; }); el("goal-result").textContent = "Goal selections cleared."; });
  el("quick-spell-search").addEventListener("input", renderQuickPicker);
  el("close-spell-picker").addEventListener("click", () => { el("spell-picker-modal").hidden = true; });
  el("close-spell-detail").addEventListener("click", () => { el("spell-detail-modal").hidden = true; });
  [el("spell-picker-modal"), el("spell-detail-modal")].forEach(modal => modal.addEventListener("click", event => { if (event.target === modal) modal.hidden = true; }));
  fetch("/static/blue_spell_farming.json?v=2").then(response => response.json()).then(payload => {
    const unique = new Map(); payload.rows.forEach(row => { if (!unique.has(row.spell)) unique.set(row.spell, row); }); spells = [...unique.values()];
    const addGoals = (container, values) => { container.innerHTML = values.map(value => `<label><input type="checkbox" value="${value}"><span>${value}</span></label>`).join(""); };
    const effectLabels = { "HP Drain": "HP Drain (Drain)", "MP Drain": "MP Drain (Aspir)", "Defense Down": "Defense Down (Dia)", "Attack Down": "Attack Down (Bio)", "Magic Defense Down": "Magic Defense Down", "Accuracy Down": "Accuracy Down", "Evasion Down": "Evasion Down", "Cure": "Restore HP (Cure)", "Paralyze": "Paralyze", "Blind": "Blind", "Silence": "Silence", "Dispel": "Dispel", "Haste": "Haste", "Stoneskin": "Stoneskin", "Blink": "Blink" };
    const effectField = document.createElement("fieldset"); effectField.innerHTML = '<legend>Additional effects / spell equivalents</legend><div id="goal-effects" class="goal-options"></div>'; el("goal-stats").closest("fieldset").before(effectField);
    addGoals(el("goal-traits"), [...new Set(spells.map(spell => spell.trait).filter(Boolean))].sort());
    const effects = [...new Set(spells.flatMap(spell => spell.effects || []))].sort(); el("goal-effects").innerHTML = effects.map(value => `<label><input type="checkbox" value="${value}"><span>${effectLabels[value] || value}</span></label>`).join("");
    addGoals(el("goal-stats"), [...new Set(spells.flatMap(spell => parseStats(spell).map(stat => stat.name)))].sort());
    render();
  }).catch(() => { el("book-catalog").innerHTML = '<p class="book-empty">Spell data could not be loaded.</p>'; });
})();
