(() => {
  document.querySelectorAll('input[name="dkp_cost"]').forEach(input => { input.step = "1"; });
  const tabs = [...document.querySelectorAll("[data-endgame-tab]")];
  const panels = [...document.querySelectorAll("[data-endgame-panel]")];
  const viewTabs = [...document.querySelectorAll("[data-endgame-view]")];
  const viewPanels = [...document.querySelectorAll("[data-endgame-view-panel]")];
  const activateView = name => {
    viewTabs.forEach(tab => tab.classList.toggle("active", tab.dataset.endgameView === name));
    viewPanels.forEach(panel => { panel.hidden = panel.dataset.endgameViewPanel !== name; });
  };
  viewTabs.forEach(tab => tab.addEventListener("click", () => {
    const name = tab.dataset.endgameView;
    activateView(name);
    if (name === "dkp-loot") activate("bidding-live");
    else if (name === "bank") history.replaceState(null, "", "#bank");
    else if (name === "operations") activate("events");
    else history.replaceState(null, "", "#calendar");
  }));
  const activate = name => {
    tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.endgameTab === name));
    panels.forEach(panel => { const active = panel.dataset.endgamePanel === name; panel.hidden = !active; panel.classList.toggle("active", active); });
    history.replaceState(null, "", `#${name}`);
  };
  tabs.forEach(tab => tab.addEventListener("click", () => activate(tab.dataset.endgameTab)));
  const requested = location.hash.slice(1);
  if (["bidding-live", "jobs", "priority", "loot", "dynamis"].includes(requested) || requested.startsWith("auction-")) { activateView("dkp-loot"); activate(requested.startsWith("auction-") ? "bidding-live" : requested); }
  else if (requested === "bank") activateView("bank");
  else if (["events", "pops", "admin-audit"].includes(requested)) { activateView("operations"); activate(requested); }
  else activateView("calendar");
  const dynamisJobFilter = document.querySelector("#dynamis-job-filter");
  const dynamisZoneFilter = document.querySelector("#dynamis-zone-filter");
  const dynamisCatalogZoneFilter = document.querySelector("#dynamis-catalog-zone-filter");
  const dynamisCatalogJobFilter = document.querySelector("#dynamis-catalog-job-filter");
  const dynamisPriorityResults = document.querySelector("#dynamis-priority-results");
  const dynamisPrioritySelection = document.querySelector("#dynamis-priority-selection");
  const refreshDynamisLots = () => {
    const job = dynamisJobFilter?.value || "";
    const matches = [...document.querySelectorAll(".dynamis-legacy-layout #dynamis-lot-body tr")]
      .map(row => ({
        name: row.cells[0]?.textContent.trim() || "",
        main: row.cells[1]?.textContent.trim() || "",
        secondary: row.cells[2]?.textContent.trim() || "",
        levels: [...(row.cells[3]?.querySelectorAll(".dynamis-eligible-job") || [])].map(entry => entry.textContent.trim()),
      }))
      .filter(row => job && (row.main === job || row.secondary === job));
    if (dynamisPriorityResults) dynamisPriorityResults.innerHTML = job
      ? (matches.length ? matches.map(row => `<article><b>${row.name}</b><span class="main">Priority · ${job} ${row.levels.find(level => level.startsWith(job))?.replace(job, "") || ""}</span></article>`).join("") : `<p>No registered priority lotters for ${job}.</p>`)
      : "<p>Choose a drop job to show its lot priority.</p>";
    const zone = dynamisCatalogZoneFilter ? dynamisCatalogZoneFilter.value : (dynamisZoneFilter?.value || "");
    const catalogJob = dynamisCatalogJobFilter?.value || "";
    document.querySelectorAll(".dynamis-lot-panel:not(.dynamis-legacy-layout) #dynamis-drop-list article").forEach(card => {
      card.hidden = Boolean((zone && card.dataset.dynamisDropArea !== zone) || (catalogJob && card.dataset.dynamisDropJob !== catalogJob));
    });
  };
  dynamisJobFilter?.addEventListener("change", refreshDynamisLots);
  dynamisZoneFilter?.addEventListener("change", () => {
    if (dynamisCatalogZoneFilter) dynamisCatalogZoneFilter.value = dynamisZoneFilter.value;
    refreshDynamisLots();
  });
  dynamisCatalogZoneFilter?.addEventListener("change", () => {
    if (dynamisZoneFilter) dynamisZoneFilter.value = dynamisCatalogZoneFilter.value;
    refreshDynamisLots();
  });
  dynamisCatalogJobFilter?.addEventListener("change", refreshDynamisLots);
  const selectDynamisCatalogItem = card => {
    const area = card.dataset.dynamisDropArea || "";
    const job = card.dataset.dynamisDropJob || "";
    const item = card.querySelector("b")?.textContent.trim() || "Selected item";
    if (dynamisCatalogZoneFilter) dynamisCatalogZoneFilter.value = area;
    if (dynamisCatalogJobFilter) dynamisCatalogJobFilter.value = job;
    if (dynamisZoneFilter) dynamisZoneFilter.value = area;
    if (dynamisJobFilter) dynamisJobFilter.value = job;
    document.querySelectorAll(".dynamis-lot-panel:not(.dynamis-legacy-layout) #dynamis-drop-list article").forEach(entry => {
      const selected = entry === card;
      entry.classList.toggle("selected", selected);
      entry.setAttribute("aria-pressed", String(selected));
    });
    if (dynamisPrioritySelection) dynamisPrioritySelection.textContent = `${item} · ${area} · ${job}`;
    refreshDynamisLots();
    dynamisPriorityResults?.scrollIntoView({behavior: "smooth", block: "nearest"});
  };
  document.querySelectorAll(".dynamis-lot-panel:not(.dynamis-legacy-layout) #dynamis-drop-list article").forEach(card => {
    card.addEventListener("click", () => selectDynamisCatalogItem(card));
    card.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectDynamisCatalogItem(card);
      }
    });
  });
  refreshDynamisLots();
  document.querySelectorAll(".dynamis-member-directory table").forEach(table => {
    const header = table.querySelector("th:nth-child(2)");
    if (header) header.textContent = "Main lot";
    table.querySelectorAll("th:nth-child(3), td:nth-child(3)").forEach(cell => { cell.hidden = false; });
    table.querySelectorAll("tbody tr").forEach(row => {
      const priority = row.cells[1];
      const job = priority?.textContent.trim();
      const level = [...(row.cells[3]?.querySelectorAll(".dynamis-eligible-job") || [])]
        .find(entry => entry.textContent.trim().startsWith(job))?.querySelector("small")?.textContent;
      if (priority && job && job !== "—" && level) priority.insertAdjacentHTML("beforeend", ` <small>${level}</small>`);
    });
  });
  document.querySelectorAll("[data-dynamis-cooldown]").forEach(node => {
    const endsAt = node.dataset.dynamisCooldown;
    const refresh = () => {
      const remaining = Math.max(0, Date.parse(endsAt) - Date.now());
      if (!remaining) { node.textContent = "Ready to request a job change."; return; }
      const days = Math.floor(remaining / 86400000);
      const hours = Math.floor((remaining % 86400000) / 3600000);
      node.textContent = `30-day lock: ${days}d ${hours}h remaining`;
    };
    refresh();
    setInterval(refresh, 60000);
  });
  const guildDateInput = document.querySelector('.event-create-form .native-date-input');
  const guildDateDisplay = document.querySelector('#guild-event-date-display');
  const guildDateButton = document.querySelector('#pick-guild-event-date');
  if (guildDateInput && guildDateButton) {
    guildDateButton.addEventListener('click', () => window.openQuarterHourPicker(guildDateInput));
    guildDateInput.addEventListener('change', () => {
      if (guildDateInput.value) {
        const [date, time] = guildDateInput.value.split('T');
        const [hour, minute] = time.split(':').map(Number);
        const rounded = Math.min(1425, Math.round((hour * 60 + minute) / 15) * 15);
        guildDateInput.value = `${date}T${String(Math.floor(rounded / 60)).padStart(2, '0')}:${String(rounded % 60).padStart(2, '0')}`;
      }
      guildDateDisplay.textContent = guildDateInput.value ? guildDateInput.value.replace('T', ' at ') : 'Choose date and time';
    });
  }

  const roster = window.ENDGAME_ROSTER || [];
  const dynamisSelections = new Map(roster.map(member => [String(member.name || "").toLowerCase(), {
    main: member.dynamis_main || "",
    secondary: member.dynamis_secondary || "",
  }]));
  document.querySelectorAll("#endgame-roster-body tr").forEach(row => {
    const selection = dynamisSelections.get(row.dataset.name) || {main: "", secondary: ""};
    row.dataset.dynamis = `${selection.main} ${selection.secondary}`.toLowerCase();
    row.children[0]?.insertAdjacentHTML("afterend", `<td><span class="job-badge main">${selection.main || "—"}</span> <span class="job-badge">${selection.secondary || "—"}</span></td>`);
  });
  const loot = window.ENDGAME_LOOT || [];
  const priorityItems = window.ENDGAME_PRIORITY_ITEMS || [];
  const jobs = window.ENDGAME_JOBS || [];
  const jobChangeKey = "hokuten-job-change-log";
  const jobChanges = JSON.parse(localStorage.getItem(jobChangeKey) || "[]");
  const adminAuditKey = "hokuten-admin-audit";
  const adminAudit = [...(window.ENDGAME_SERVER_AUDIT || []), ...JSON.parse(localStorage.getItem(adminAuditKey) || "[]")];
  let auditSort = {key: "at", direction: -1};
  const safeText = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[character]));
  const bankSearch = document.querySelector("#ls-bank-search");
  const bankHolderFilter = document.querySelector("#ls-bank-holder-filter");
  const bankStatusFilter = document.querySelector("#ls-bank-status-filter");
  const filterBankRows = () => {
    const query = bankSearch?.value.trim().toLowerCase() || "";
    const holder = bankHolderFilter?.value || "";
    const status = bankStatusFilter?.value || "";
    let visible = 0;
    document.querySelectorAll("#ls-bank-body tr[data-bank-search]").forEach(row => {
      const matches = (!query || row.dataset.bankSearch.includes(query)) && (!holder || row.dataset.holder === holder) && (!status || row.dataset.status === status);
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    const count = document.querySelector("#bank-filter-count");
    if (count) count.textContent = `${visible} matching / ${document.querySelectorAll("#ls-bank-body tr[data-bank-search]").length} entries`;
  };
  [bankSearch, bankHolderFilter, bankStatusFilter].filter(Boolean).forEach(control => {
    ["input", "change"].forEach(eventName => control.addEventListener(eventName, filterBankRows));
  });
  const bankMarketKey = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  const formatBankGil = value => `${Math.max(0, Math.round(Number(value) || 0)).toLocaleString()}g`;
  const bankItemInput = document.querySelector("#ls-bank-item");
  const bankItemCatalog = document.querySelector("#ls-bank-item-catalog");
  let bankCanonicalItemNames = new Map();
  let bankCatalogNames = [];
  const showBankItemSuggestions = () => {
    if (!bankItemInput || !bankItemCatalog) return;
    const query = bankMarketKey(bankItemInput.value);
    const matches = query.length >= 2 ? bankCatalogNames.filter(name => bankMarketKey(name).includes(query)).slice(0, 12) : [];
    bankItemCatalog.replaceChildren(...matches.map(name => {
      const option = document.createElement("button");
      option.type = "button";
      option.setAttribute("role", "option");
      option.textContent = name;
      option.addEventListener("mousedown", event => {
        event.preventDefault();
        bankItemInput.value = name;
        bankItemCatalog.hidden = true;
        bankItemInput.setAttribute("aria-expanded", "false");
      });
      return option;
    }));
    bankItemCatalog.hidden = matches.length === 0;
    bankItemInput.setAttribute("aria-expanded", String(matches.length > 0));
  };
  const updateBankItemCatalog = prices => {
    if (!bankItemCatalog) return;
    bankCatalogNames = [...new Set(Object.values(prices || {}).map(price => String(price?.name || "").trim()).filter(Boolean))]
      .sort((left, right) => left.localeCompare(right));
    bankCanonicalItemNames = new Map(bankCatalogNames.map(name => [bankMarketKey(name), name]));
    showBankItemSuggestions();
  };
  bankItemInput?.addEventListener("input", showBankItemSuggestions);
  bankItemInput?.addEventListener("focus", showBankItemSuggestions);
  bankItemInput?.addEventListener("blur", () => setTimeout(() => {
    if (bankItemCatalog) bankItemCatalog.hidden = true;
    bankItemInput?.setAttribute("aria-expanded", "false");
  }, 120));
  bankItemInput?.form?.addEventListener("submit", () => {
    const canonical = bankCanonicalItemNames.get(bankMarketKey(bankItemInput.value));
    if (canonical) bankItemInput.value = canonical;
  });
  const updateBankMarketValues = prices => {
    const byName = Object.fromEntries(Object.values(prices || {}).filter(price => price.name).map(price => [bankMarketKey(price.name), price]));
    let heldValue = 0;
    document.querySelectorAll(".bank-market-value").forEach(cell => {
      const price = byName[bankMarketKey(cell.dataset.bankItem)];
      const candidates = [price?.bazaar_lowest, price?.single_recent_average, price?.single_average]
        .filter(value => value !== null && value !== undefined && value !== "")
        .map(Number).filter(value => Number.isFinite(value) && value > 0);
      const unit = candidates.length ? Math.min(...candidates) : null;
      if (unit == null) { cell.textContent = "—"; cell.title = "No PSXI market value is currently available."; return; }
      const value = Number(unit) * Number(cell.dataset.bankQuantity || 1);
      heldValue += value;
      cell.closest("tr").dataset.market = String(value);
      cell.textContent = formatBankGil(value);
      const source = Number(price?.bazaar_lowest) === unit ? "lowest bazaar listing" : "sale average";
      cell.title = `PSXI ${source}: ${formatBankGil(unit)} each`;
    });
    const cash = Number(document.querySelector(".ls-bank-summary")?.dataset.bankCash || 0);
    const held = document.querySelector("#bank-held-market");
    const total = document.querySelector("#bank-total-value");
    if (held) held.textContent = formatBankGil(heldValue);
    if (total) total.textContent = formatBankGil(cash + heldValue);
    filterBankRows();
  };
  const refreshBankMarket = () => {
    const buttons = [...document.querySelectorAll(".refresh-bank-market")];
    buttons.forEach(control => { control.disabled = true; control.textContent = "Refreshing…"; });
    return fetch("/api/market-prices?refresh=1", {headers: {"Accept": "application/json"}})
      .then(response => response.ok ? response.json() : Promise.reject())
      .then(snapshot => { updateBankItemCatalog(snapshot.prices); updateBankMarketValues(snapshot.prices); })
      .catch(() => document.querySelectorAll(".bank-market-value").forEach(cell => { cell.textContent = "Market unavailable"; }))
      .finally(() => buttons.forEach(control => { control.disabled = false; control.textContent = "Refresh market"; }));
  };
  document.querySelectorAll(".refresh-bank-market").forEach(button => button.addEventListener("click", refreshBankMarket));
  if (document.querySelector(".ls-bank-panel")) {
    filterBankRows();
    fetch("/api/market-prices", {headers: {"Accept": "application/json"}})
      .then(response => response.ok ? response.json() : Promise.reject())
      .then(snapshot => { updateBankItemCatalog(snapshot.prices); updateBankMarketValues(snapshot.prices); })
      .catch(() => document.querySelectorAll(".bank-market-value").forEach(cell => { cell.textContent = "Market unavailable"; }));
  }
  let bankSort = {key: "item", direction: 1};
  document.querySelectorAll("[data-bank-sort]").forEach(button => button.addEventListener("click", () => {
    const key = button.dataset.bankSort;
    bankSort = {key, direction: bankSort.key === key ? -bankSort.direction : 1};
    document.querySelectorAll("[data-bank-sort]").forEach(control => {
      control.classList.toggle("active", control === button);
      control.querySelector("span").textContent = control === button ? (bankSort.direction > 0 ? "ASC" : "DESC") : "Sort";
    });
    const type = button.dataset.sortType;
    const body = document.querySelector("#ls-bank-body");
    if (!body) return;
    [...body.rows].sort((left, right) => {
      const a = left.dataset[key] || "", b = right.dataset[key] || "";
      return (type === "number" ? Number(a) - Number(b) : a.localeCompare(b, undefined, {numeric: true})) * bankSort.direction;
    }).forEach(row => body.appendChild(row));
  }));
  if (dynamisCatalogZoneFilter && ![...dynamisCatalogZoneFilter.options].some(option => option.value === "")) {
    dynamisCatalogZoneFilter.prepend(new Option("All Dynamis zones", ""));
  }
  const dynamisCatalogTooltips = new Map((window.ENDGAME_DYNAMIS_CATALOG || []).map(drop => [drop.item, drop.tooltip || {}]));
  const dynamisItemTooltip = document.createElement("aside");
  dynamisItemTooltip.className = "auction-item-tooltip dynamis-item-tooltip";
  dynamisItemTooltip.hidden = true;
  dynamisItemTooltip.setAttribute("role", "tooltip");
  document.body.append(dynamisItemTooltip);
  const positionDynamisTooltip = (x, y) => {
    const width = dynamisItemTooltip.offsetWidth || 390;
    const height = dynamisItemTooltip.offsetHeight || 220;
    dynamisItemTooltip.style.left = `${Math.max(10, Math.min(innerWidth - width - 10, x + 14))}px`;
    dynamisItemTooltip.style.top = `${Math.max(10, Math.min(innerHeight - height - 10, y + 14))}px`;
  };
  document.querySelectorAll(".dynamis-lot-panel:not(.dynamis-legacy-layout) #dynamis-drop-list article").forEach(card => {
    const item = dynamisCatalogTooltips.get(card.querySelector("b")?.textContent.trim());
    if (!item) return;
    card.classList.add("dynamis-tooltip-target");
    card.tabIndex = 0;
    const show = (x, y) => {
      const rarity = item.rare && item.ex ? "Rare/Ex" : item.rare ? "Rare" : item.ex ? "Ex" : "";
      dynamisItemTooltip.innerHTML = `${item.item_id ? `<img src="https://static.ffxiah.com/images/icon/${item.item_id}.png" alt="">` : ""}<div><strong>${safeText(item.name)}</strong><span>${rarity ? `${rarity} · ` : ""}Level ${item.level || "—"} · ${safeText((item.slots || []).join(" / "))}</span><p>${safeText(item.description || "No item stats available.")}</p><small>${safeText((item.jobs || []).join(" / "))}</small></div>`;
      dynamisItemTooltip.hidden = false;
      positionDynamisTooltip(x, y);
    };
    card.addEventListener("mouseenter", event => show(event.clientX, event.clientY));
    card.addEventListener("mousemove", event => positionDynamisTooltip(event.clientX, event.clientY));
    card.addEventListener("mouseleave", () => { dynamisItemTooltip.hidden = true; });
    card.addEventListener("focus", () => { const box = card.getBoundingClientRect(); show(box.right, box.top); });
    card.addEventListener("blur", () => { dynamisItemTooltip.hidden = true; });
  });
  const priorityLabel = value => ({"Main priority":"P1","Secondary priority":"P2","P1 Auction":"P1","P2 Auction":"P2","P3 Auction":"P3"}[value] || value || "Freelot");
  const auctionRoot = document.querySelector("#active-auctions");
  const openLiveAuction = () => {
    activateView("dkp-loot");
    activate("bidding-live");
    requestAnimationFrame(() => auctionRoot?.scrollIntoView({behavior: "smooth", block: "start"}));
  };
  window.addEventListener("endgame:open-live-auction", openLiveAuction);
  let auctionEditingUntil = 0;
  let auctionRecords = new Map();
  let pastAuctionsOpen = false;
  const auctionEditing = () => Date.now() < auctionEditingUntil || Boolean(
    document.activeElement?.closest?.(".auction-bid-form, .auction-winner-select")
  );
  let auctionTooltips = {};
  const auctionError = message => `<p class="auction-message error">${safeText(message)}</p>`;
  const countdownText = endsAt => {
    const seconds = Math.max(0, Math.ceil((Date.parse(`${endsAt}Z`) - Date.now()) / 1000));
    return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  };
  const activityTimestamp = value => {
    const parsed = Date.parse(String(value || "").includes("T") ? value : `${value}Z`);
    return Number.isNaN(parsed) ? "" : new Date(parsed).toLocaleString([], {month: "short", day: "numeric", hour: "numeric", minute: "2-digit"});
  };
  const renderAuctions = payload => {
    if (!auctionRoot) return;
    const currentAuctions = payload.current_auctions || payload.auctions.filter(auction => auction.status !== "Confirmed");
    const pastAuctions = payload.past_auctions || payload.auctions.filter(auction => auction.status === "Confirmed");
    const displayedAuctions = [...currentAuctions, ...pastAuctions];
    document.querySelectorAll('[data-auction-metric="my-dkp"]').forEach(metric => { metric.textContent = `${payload.my_available} DKP${payload.my_reserved ? ` (${payload.my_reserved} committed)` : ""}`; });
    document.querySelectorAll('[data-auction-metric="bid-cap"]').forEach(metric => { metric.textContent = `${payload.dkp.cap} DKP`; });
    document.querySelectorAll('[data-auction-metric="highest-dkp"]').forEach(metric => { metric.textContent = `${payload.dkp.highest} DKP`; });
    auctionTooltips = Object.fromEntries(payload.auctions.flatMap(auction => auction.items.map(item => [String(item.id), item.tooltip || {}])));
    auctionRecords = new Map(payload.auctions.map(auction => [String(auction.id), auction]));
    auctionRoot.innerHTML = displayedAuctions.length ? displayedAuctions.map((auction, index) => {
      const active = auction.status === "Active";
      const completed = auction.status === "Confirmed";
      const acceptingBids = active && !auction.paused;
      const items = auction.items.map(item => {
        const bids = item.bids.length ? item.bids.map((bid, index) => `<li class="${index === 0 ? "leading" : ""}"><span><b>${safeText(bid.name)}</b> ${safeText(bid.job)} · P${bid.tier === 4 ? "Free" : bid.tier}</span><strong>${bid.amount} DKP</strong></li>`).join("") : '<li class="no-bids">No bids yet</li>';
        const jobOptions = item.eligible_jobs.map(entry => `<option value="${entry.job}" ${item.my_bid?.job === entry.job ? "selected" : ""}>${entry.job} · Lv.${entry.level} · ${entry.tier === 4 ? "Freelot" : `P${entry.tier}`}</option>`).join("");
        const bidderOptions = item.bids.map(bid => `<option value="${bid.member_id}" ${bid.member_id === item.suggested_winner_id ? "selected" : ""}>${safeText(bid.name)} · ${bid.job} · ${bid.amount} DKP · P${bid.tier === 4 ? "Free" : bid.tier}</option>`).join("");
        return `<article class="auction-item-card"><header><div><h4><button class="auction-tooltip-target" type="button" data-auction-tooltip="${item.id}">${safeText(item.item)}</button></h4><small>${item.target_item && item.target_item !== item.item ? `${safeText(item.target_item)} · ` : ""}${safeText(item.family)} · Lv.${item.required_level}</small></div><b>${item.bids.length} bid${item.bids.length === 1 ? "" : "s"}</b></header><ol class="auction-bid-list">${bids}</ol>${acceptingBids ? (jobOptions ? `<form class="auction-bid-form" data-auction-item="${item.id}"><select name="job" required><option value="">Eligible job</option>${jobOptions}</select><input type="number" name="amount" min="1" max="${item.max_bid}" value="${item.my_bid?.amount || ""}" placeholder="DKP" required><button type="submit">${item.my_bid ? "Update Bid" : "Place Bid"}</button><small class="auction-bid-budget">Up to ${item.max_bid} DKP; increasing this may reduce other active bids</small></form>` : '<p class="auction-ineligible">No eligible leveled job for this item.</p>') : (active ? '<p class="auction-paused-note">Bidding is paused by leadership.</p>' : `<label class="auction-winner-select">Confirmed winner<select name="winner_${item.id}" form="confirm-auction-${auction.id}"><option value="">No award</option>${bidderOptions}</select></label>`)}</article>`;
      }).join("");
      const pauseControl = active && payload.is_admin ? `<form class="auction-pause-form" method="post" action="/endgame/auctions/${auction.id}/pause"><input type="hidden" name="csrf_token" value="${safeText(window.ENDGAME_CSRF)}"><button type="submit">${auction.paused ? "Resume Auction" : "Pause Auction"}</button></form>` : "";
      const completeControl = active && payload.is_admin ? `<form class="auction-complete-form" method="post" action="/endgame/auctions/${auction.id}/complete"><input type="hidden" name="csrf_token" value="${safeText(window.ENDGAME_CSRF)}"><button type="submit">Stop &amp; Complete</button></form>` : "";
      const stopControl = active && payload.is_admin ? `<form class="auction-discard-form" method="post" action="/endgame/auctions/${auction.id}/delete"><input type="hidden" name="csrf_token" value="${safeText(window.ENDGAME_CSRF)}"><button class="danger" type="submit">Stop &amp; Delete Auction</button></form>` : "";
      const sectionHeading = (currentAuctions.length && index === 0) ? `<h3 class="auction-section-title">Current Auctions</h3>` : (pastAuctions.length && index === currentAuctions.length ? `<h3 class="auction-section-title">Past Auctions</h3>` : "");
      return `${sectionHeading}<section id="auction-${auction.id}" class="auction-card ${active ? "active" : "closed"} ${completed ? "completed" : ""} ${auction.paused ? "paused" : ""}"><header><div><span>${safeText(auction.area)} · ${safeText(auction.event_name)}</span><h3>${safeText(auction.boss)}</h3>${pauseControl}${completeControl}${stopControl}</div><div class="auction-clock"><small>${completed ? "Winners / DKP Completed" : (auction.paused ? "Countdown frozen" : (active ? "Bidding closes in" : "Bidding closed"))}</small><b data-auction-ends="${auction.ends_at}" data-auction-paused="${auction.paused ? "true" : "false"}">${auction.paused ? "PAUSED" : (active ? countdownText(auction.ends_at) : "00:00")}</b></div></header>${!active && !completed && payload.is_admin ? `<form id="confirm-auction-${auction.id}" class="auction-confirm-form" method="post" action="/endgame/auctions/${auction.id}/confirm"><input type="hidden" name="csrf_token" value="${safeText(window.ENDGAME_CSRF)}"><p>Review the suggested winners, then confirm the items that actually dropped.</p></form>` : ""}<div class="auction-item-grid">${items}</div>${!active && !completed && payload.is_admin ? `<button class="button primary auction-confirm-button" type="submit" form="confirm-auction-${auction.id}">Confirm Winners &amp; Deduct DKP</button>` : ""}${completed ? `<p class="auction-completed-note">Winners / DKP Completed${auction.award_count ? ` · ${auction.award_count} award${auction.award_count === 1 ? "" : "s"}` : ""}</p>` : ""}</section>`;
    }).join("") : '<p class="event-empty">No active or recently closed auctions. An administrator can start one for an Endgame event above.</p>';
    displayedAuctions.filter(auction => auction.status === "Confirmed").forEach(auction => {
      const cards = [...document.querySelectorAll(`#auction-${auction.id} .auction-item-card`)];
      auction.items.forEach((item, index) => {
        if (!item.awards?.length || !cards[index]) return;
        cards[index].querySelector(".auction-bid-list")?.insertAdjacentHTML("afterend", `<div class="auction-award-summary">${item.awards.map(award => `<span><b>${safeText(award.recipient)}</b> · ${safeText(award.job)} · ${Number(award.dkp_cost)} DKP · ${safeText(award.distribution)}</span>`).join("")}</div>`);
      });
    });
    displayedAuctions.forEach(auction => {
      const card = document.getElementById(`auction-${auction.id}`);
      const heading = card?.querySelector("header h3");
      if (heading) heading.textContent = `Auction #${auction.id} / ${auction.boss}`;
    });
    if (pastAuctions.length) {
      const firstPastCard = document.getElementById(`auction-${pastAuctions[0].id}`);
      const archive = document.createElement("details");
      archive.className = "past-auctions-archive";
      archive.innerHTML = `<summary>Past Auctions <span>${pastAuctions.length}</span></summary><div class="past-auctions-list"></div>`;
      archive.open = pastAuctionsOpen;
      archive.addEventListener("toggle", () => { pastAuctionsOpen = archive.open; });
      firstPastCard?.previousElementSibling?.classList.contains("auction-section-title") && firstPastCard.previousElementSibling.remove();
      firstPastCard?.before(archive);
      const list = archive.querySelector(".past-auctions-list");
      pastAuctions.forEach(auction => list?.append(document.getElementById(`auction-${auction.id}`)));
    }
    // Closed auctions are deliberately kept until an administrator confirms them.
    // A separate discard control makes it safe to clear test auctions without touching DKP.
    if (payload.is_admin) {
      auctionRoot.querySelectorAll(".auction-card.active .auction-discard-form").forEach(form => {
        form.addEventListener("submit", event => {
          if (!confirm("Stop and delete this auction? All bids will be cleared and no DKP will be deducted.")) event.preventDefault();
        });
      });
      payload.auctions.filter(auction => auction.status === "Closed" || auction.status === "Confirmed").forEach(auction => {
        const card = document.getElementById(`auction-${auction.id}`);
        if (!card) return;
        const actions = document.createElement("form");
        actions.className = "auction-discard-form";
        actions.method = "post";
        actions.action = `/endgame/auctions/${auction.id}/delete`;
        actions.innerHTML = `<input type="hidden" name="csrf_token" value="${safeText(window.ENDGAME_CSRF)}"><button type="submit">${auction.status === "Confirmed" ? "Discard &amp; Reverse DKP" : "Discard Auction"}</button>`;
        actions.addEventListener("submit", event => {
          const warning = auction.status === "Confirmed" ? "Discard this confirmed auction and reverse its linked DKP awards?" : "Discard this closed auction? No DKP will be deducted.";
          if (!confirm(warning)) event.preventDefault();
        });
        card.querySelector("header > div")?.append(actions);
        const reopen = document.createElement("form");
        reopen.className = "auction-reopen-form";
        reopen.method = "post";
        reopen.action = `/endgame/auctions/${auction.id}/reopen`;
        reopen.innerHTML = `<input type="hidden" name="csrf_token" value="${safeText(window.ENDGAME_CSRF)}"><button type="submit">Reopen for Editing</button>`;
        reopen.addEventListener("submit", event => {
          if (!confirm("Reopen this auction for five minutes? Linked DKP awards will be restored so winners can be corrected.")) event.preventDefault();
        });
        card.querySelector("header > div")?.append(reopen);
      });
      pastAuctions.forEach(auction => {
        const card = document.getElementById(`auction-${auction.id}`);
        card?.querySelectorAll(".auction-winner-select").forEach(control => {
          const note = document.createElement("p");
          note.className = "auction-completed-note";
          note.textContent = "Winners / DKP Completed";
          control.replaceWith(note);
        });
      });
    }
    pastAuctions.forEach(auction => {
      const card = document.getElementById(`auction-${auction.id}`);
      card?.querySelectorAll(".auction-winner-select").forEach(control => {
        const note = document.createElement("p");
        note.className = "auction-completed-note";
        note.textContent = "Winners / DKP Completed";
        control.replaceWith(note);
      });
    });
    auctionRoot.querySelectorAll(".auction-bid-list li span, .auction-winner-select option").forEach(entry => {
      entry.innerHTML = entry.innerHTML.replace("PFree", "Freelot");
    });
    const recent = document.querySelector("#recent-auction-bids");
    recent.innerHTML = payload.recent_bids.length ? payload.recent_bids.map(bid => `<article><span><b>${safeText(bid.name)}</b> bid on ${safeText(bid.item)}<small>${safeText(bid.boss)} · ${safeText(bid.job)} · ${safeText(activityTimestamp(bid.updated_at))}</small></span><strong>${bid.amount} DKP</strong></article>`).join("") : '<p class="event-empty">No bids have been placed.</p>';
  };
  const loadAuctions = async () => {
    if (!auctionRoot) return;
    if (auctionEditing()) return;
    try {
      const response = await fetch("/api/endgame/auctions", {headers: {"Accept": "application/json"}});
      if (!response.ok) throw new Error("Could not refresh bidding.");
      const payload = await response.json();
      if (auctionEditing()) return;
      renderAuctions(payload);
      const auctionAnchor = location.hash.slice(1);
      if (auctionAnchor.startsWith("auction-")) {
        requestAnimationFrame(() => document.getElementById(auctionAnchor)?.scrollIntoView({behavior: "smooth", block: "start"}));
      }
      const state = document.querySelector("#auction-refresh-state");
      if (state) state.textContent = `Updated ${new Date().toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"})}`;
    } catch (error) { auctionRoot.innerHTML = auctionError(error.message); }
  };
  document.addEventListener("submit", async event => {
    const form = event.target.closest(".auction-bid-form");
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector("button"); button.disabled = true;
    try {
      const values = new FormData(form);
      const response = await fetch(`/api/endgame/auction-items/${form.dataset.auctionItem}/bid`, {method: "POST", headers: {"Content-Type": "application/json", "X-CSRF-Token": window.ENDGAME_CSRF}, body: JSON.stringify({job: values.get("job"), amount: values.get("amount")})});
      if (!response.ok) { const text = await response.text(); throw new Error(text.match(/<p>(.*?)<\/p>/s)?.[1] || "The bid could not be placed."); }
      const result = await response.json();
      renderAuctions(result.auction);
      if (result.adjusted?.length) alert(`Bid updated. To keep your total within your DKP, these bids were adjusted:\n${result.adjusted.map(row => `${row.item}: ${row.from} → ${row.to} DKP`).join("\n")}`);
    } catch (error) { alert(error.message); button.disabled = false; }
  });
  if (auctionRoot) {
    auctionRoot.addEventListener("input", event => { if (event.target.closest(".auction-bid-form")) auctionEditingUntil = Date.now() + 15000; });
    auctionRoot.addEventListener("change", event => {
      if (event.target.closest(".auction-bid-form")) auctionEditingUntil = Date.now() + 15000;
      if (event.target.closest(".auction-winner-select")) auctionEditingUntil = Date.now() + 600000;
    });
    loadAuctions();
    setInterval(loadAuctions, 3000);
    setInterval(() => document.querySelectorAll("[data-auction-ends]").forEach(clock => { if (clock.dataset.auctionPaused !== "true") clock.textContent = countdownText(clock.dataset.auctionEnds); }), 1000);
  }
  const auctionTooltip = document.querySelector("#auction-item-tooltip");
  const placeAuctionTooltip = (x, y) => {
    if (!auctionTooltip || auctionTooltip.hidden) return;
    const gap = 14, width = auctionTooltip.offsetWidth, height = auctionTooltip.offsetHeight;
    auctionTooltip.style.left = `${Math.max(10, Math.min(innerWidth - width - 10, x + gap))}px`;
    auctionTooltip.style.top = `${Math.max(10, Math.min(innerHeight - height - 10, y + gap))}px`;
  };
  const showAuctionTooltip = (target, x, y) => {
    const item = auctionTooltips[target.dataset.auctionTooltip];
    if (!auctionTooltip || !item) return;
    const rarity = [item.rare ? "Rare" : "", item.ex ? "Ex" : ""].filter(Boolean).join("/");
    auctionTooltip.innerHTML = `${item.item_id ? `<img src="https://static.ffxiah.com/images/icon/${item.item_id}.png" alt="">` : ""}<div><strong>${safeText(item.name)}</strong><span>${rarity ? `${rarity} · ` : ""}Level ${item.level || "—"} · ${safeText((item.slots || []).join(" / "))}</span><p>${safeText(item.description || "No item stats available.")}</p><small>${safeText((item.jobs || []).join(" / "))}</small></div>`;
    auctionTooltip.hidden = false; placeAuctionTooltip(x, y);
  };
  document.addEventListener("pointerover", event => { const target = event.target.closest("[data-auction-tooltip]"); if (target) showAuctionTooltip(target, event.clientX, event.clientY); });
  document.addEventListener("pointermove", event => placeAuctionTooltip(event.clientX, event.clientY));
  document.addEventListener("pointerout", event => { if (event.target.closest("[data-auction-tooltip]") && !event.relatedTarget?.closest?.("[data-auction-tooltip]")) auctionTooltip.hidden = true; });
  document.addEventListener("focusin", event => { const target = event.target.closest("[data-auction-tooltip]"); if (target) { const box = target.getBoundingClientRect(); showAuctionTooltip(target, box.right, box.top); } });
  document.addEventListener("focusout", event => { if (event.target.closest("[data-auction-tooltip]") && auctionTooltip) auctionTooltip.hidden = true; });
  const renderAdminAudit = () => {
    const body = document.querySelector("#admin-audit-body");
    if (!body) return;
    const filters = [...document.querySelectorAll("[data-audit-filter]")].reduce((values, control) => ({...values, [control.dataset.auditFilter]: control.value.trim().toLowerCase()}), {});
    const rows = adminAudit.filter(row => Object.entries(filters).every(([key, wanted]) => !wanted || String(row[key] ?? "").toLowerCase().includes(wanted))).sort((left, right) => {
      if (auditSort.key === "at") return ((Date.parse(left.at) || 0) - (Date.parse(right.at) || 0)) * auditSort.direction;
      return String(left[auditSort.key] ?? "").localeCompare(String(right[auditSort.key] ?? ""), undefined, {numeric: true}) * auditSort.direction;
    });
    body.innerHTML = rows.length ? rows.map(row => `<tr><td>${safeText(row.at)}</td><td><b>${safeText(row.actor)}</b></td><td>${safeText(row.area)}</td><td>${safeText(row.action)}</td><td>${safeText(row.details)}</td></tr>`).join("") : '<tr><td colspan="5">No administrator changes match the current filters.</td></tr>';
  };
  const recordAdminChange = (area, action, details) => {
    adminAudit.push({at: new Date().toLocaleString(), actor: window.ENDGAME_ACTOR || "Administrator", area, action, details});
    localStorage.setItem(adminAuditKey, JSON.stringify(adminAudit));
    renderAdminAudit();
  };
  renderAdminAudit();
  const auditFilters = [...document.querySelectorAll("[data-audit-filter]")];
  auditFilters.forEach(control => control.addEventListener("input", renderAdminAudit));
  document.querySelector(".clear-audit-filters")?.addEventListener("click", () => {
    auditFilters.forEach(control => { control.value = ""; });
    renderAdminAudit();
  });
  document.querySelectorAll("[data-audit-sort]").forEach(button => button.addEventListener("click", () => {
    const key = button.dataset.auditSort;
    auditSort = {key, direction: auditSort.key === key ? -auditSort.direction : 1};
    document.querySelectorAll("[data-audit-sort]").forEach(control => {
      control.classList.toggle("active", control === button);
      control.querySelector("span").textContent = control === button ? (auditSort.direction > 0 ? "ASC" : "DESC") : "Sort";
    });
    renderAdminAudit();
  }));
  const refreshJobCooldowns = () => document.querySelectorAll("[data-job-cooldown-until]").forEach(label => {
    const remaining = Math.max(0, Date.parse(label.dataset.jobCooldownUntil) - Date.now());
    if (!remaining) { label.hidden = true; return; }
    const days = Math.floor(remaining / 86400000);
    const hours = Math.floor((remaining % 86400000) / 3600000);
    label.textContent = `Job change: ${days}d ${hours}h remaining`;
  });
  refreshJobCooldowns();
  setInterval(refreshJobCooldowns, 60000);
  const jobHistory = (member, slot) => jobChanges.filter(row => row.member === member && row.slot === slot);
  const jobHistoryLabel = (member, slot) => {
    const changes = jobHistory(member, slot);
    if (!changes.length) return "No changes recorded";
    return changes.slice(-5).reverse().map(row => `${row.from || "Unassigned"} to ${row.to || "Unassigned"}\n${row.at} by ${row.actor}`).join("\n\n");
  };
  const updateJobDisplay = (member, slot, value) => {
    const record = roster.find(row => row.name === member);
    if (record) record[slot] = value;
    const badge = document.querySelector(`[data-job-member="${CSS.escape(member)}"][data-job-slot="${slot}"]`);
    if (badge) {
      badge.textContent = value || (slot === "main_job" ? "Unassigned" : "None");
      badge.dataset.jobHistory = jobHistoryLabel(member, slot);
      const tableRow = badge.closest("tr");
      if (tableRow && record) {
        tableRow.dataset.jobs = `${record.main_job || ""} ${record.secondary_job || ""}`.toLowerCase();
        tableRow.dataset[slot === "main_job" ? "main" : "secondary"] = (value || "").toLowerCase();
      }
    }
  };
  if (window.ENDGAME_IS_ADMIN) {
    roster.forEach(member => ["main_job", "secondary_job"].forEach(slot => {
      const changes = jobHistory(member.name, slot);
      updateJobDisplay(member.name, slot, changes.length ? changes[changes.length - 1].to : member[slot]);
    }));
  }
  const priorityBody = document.querySelector("#priority-body");
  const priorityJob = {value: "", addEventListener: () => {}};
  const priorityItem = document.querySelector("#priority-item");
  const priorityMajor = document.querySelector("#priority-major");
  const lastDate = value => value === "—" ? 0 : new Date(value).getTime();
  const rankPriority = () => {
    const job = priorityJob.value;
    const major = priorityMajor.value === "major";
    const candidates = roster.map(member => ({...member, jobStatus: member.main_job === job ? 1 : member.secondary_job === job ? 2 : 9}))
      .filter(member => member.jobStatus < 9)
      .sort((a, b) => a.jobStatus - b.jobStatus || a.tier - b.tier || (major ? Number(a.cooldown) - Number(b.cooldown) : 0) || a.major_wins - b.major_wins || lastDate(a.last_major_win) - lastDate(b.last_major_win) || a.name.localeCompare(b.name));
    document.querySelector("#priority-title").textContent = `${priorityItem.value || "Selected item"} · ${job || "Choose a job"}`;
    document.querySelector("#priority-note").textContent = candidates.length ? `${candidates.length} registered candidates. Eligibility checks still apply at the event.` : "No member has this job registered as Main or Secondary.";
    priorityBody.innerHTML = candidates.map((member, index) => {
      const explanation = member.jobStatus === 1 ? (member.tier === 1 ? "Main job · strongest attendance tier" : `Main job · Tier ${member.tier}`) : "Secondary job; follows all Main Job candidates";
      return `<tr><td><span class="rank-number ${index === 0 ? "top" : ""}">${index + 1}</span></td><td><b>${member.name}</b></td><td><span class="job-badge ${member.jobStatus === 1 ? "main" : ""}">${member.jobStatus === 1 ? "Main" : "Secondary"} ${job}</span></td><td><span class="tier tier-${member.tier}">Tier ${member.tier} · ${member.attendance}%</span></td><td><span class="cooldown ${member.cooldown ? "locked" : "ready"}">${member.cooldown ? "Cooldown" : "Ready"}</span></td><td>${member.major_wins}</td><td>${member.last_major_win}</td><td><small>${explanation}</small></td></tr>`;
    }).join("") || '<tr><td colspan="8">Choose a receiving job to calculate priority.</td></tr>';
  };
  [priorityJob, priorityItem, priorityMajor].forEach(control => control.addEventListener("input", rankPriority)); rankPriority();

  const rankMatrixPriority = () => {
    const item = priorityItems.find(row => row.name === priorityItem.value);
    if (!item) {
      document.querySelector("#priority-source").value = "";
      document.querySelector("#priority-title").textContent = "Select an item";
      document.querySelector("#priority-note").textContent = "Source, item family, job tiers, and calculated priority will appear automatically.";
      document.querySelector("#priority-tiers").innerHTML = "";
      priorityBody.innerHTML = '<tr><td colspan="8">Select a Sky or Sea drop to calculate priority.</td></tr>';
      return;
    }
    const tierFor = job => item.freelot ? 4 : item.p1.includes(job) ? 1 : item.p2.includes(job) ? 2 : item.p3.includes(job) ? 3 : 99;
    const candidates = roster.map(member => {
      const canEquip = job => job && Number((member.job_levels || {})[job] || 0) >= Number(item.required_level || 1);
      const mainTier = canEquip(member.main_job) ? tierFor(member.main_job) : 99;
      const secondaryTier = canEquip(member.secondary_job) ? tierFor(member.secondary_job) : 99;
      const useMain = mainTier <= secondaryTier;
      return {...member, priorityTier: Math.min(mainTier, secondaryTier), jobStatus: useMain ? 1 : 2, eligibleJob: useMain ? member.main_job : member.secondary_job};
    }).filter(member => member.priorityTier < 99 && (item.freelot || member.eligibleJob))
      .sort((a, b) => a.priorityTier - b.priorityTier || b.dkp - a.dkp || a.name.localeCompare(b.name));
    document.querySelector("#priority-source").value = `${item.area} / ${item.source}`;
    document.querySelector("#priority-title").textContent = `${item.name} / ${item.source}`;
    document.querySelector("#priority-note").textContent = candidates.length ? `${candidates.length} candidates meet the Lv.${item.required_level || 1} equipment requirement, grouped by P1/P2/P3 and sorted by DKP. Only P1 candidates may bid.` : `No registered member has an eligible job at Lv.${item.required_level || 1}.`;
    document.querySelector("#priority-tiers").innerHTML = item.freelot ? '<article class="freelot"><span>Distribution</span><b>Freelot</b><small>Attendance and general eligibility still apply.</small></article>' : [1,2,3].map(tier => `<article><span>P${tier}</span><b>${(item[`p${tier}`] || []).join(" / ") || "None"}</b><small>${tier === 1 ? "First consideration" : tier === 2 ? "After eligible P1 jobs" : "After eligible P1 and P2 jobs"}</small></article>`).join("");
    let previousRankKey = "", displayedRank = 0;
    priorityBody.innerHTML = candidates.map((member, index) => {
      const rankKey = `${member.priorityTier}|${member.dkp}`;
      if (rankKey !== previousRankKey) displayedRank = index + 1;
      previousRankKey = rankKey;
      const label = item.freelot ? "Freelot" : `P${member.priorityTier}`;
      const canBid = item.freelot || member.priorityTier === 1;
      const explanation = item.freelot ? "Freelot; normal event rules apply" : canBid ? `P1 ${member.eligibleJob}; eligible to bid up to available DKP` : `${label} fallback; P1 must clear first`;
      return `<tr><td><span class="rank-number ${displayedRank === 1 ? "top" : ""}">${displayedRank}</span></td><td><b>${member.name}</b></td><td><span class="job-badge ${member.priorityTier === 1 ? "main" : ""}">${label} / ${member.eligibleJob || ""} Lv.${(member.job_levels || {})[member.eligibleJob] || 0}</span></td><td><strong class="dkp-balance">${member.dkp}</strong></td><td><span class="dkp-bid-status ${canBid ? "eligible" : "waiting"}">${canBid ? "May bid" : "Waiting tier"}</span></td><td><small>${explanation}</small></td></tr>`;
    }).join("") || '<tr><td colspan="6">No eligible registered members for this item.</td></tr>';
  };
  [priorityItem, priorityMajor].forEach(control => control.addEventListener("input", rankMatrixPriority));
  rankMatrixPriority();

  const rosterSearch = document.querySelector("#endgame-roster-search");
  const columnFilters = [...document.querySelectorAll("[data-roster-filter]")];
  const filterRoster = () => document.querySelectorAll("#endgame-roster-body tr").forEach(row => {
    const query = rosterSearch.value.toLowerCase();
    const columnMatch = columnFilters.every(control => {
      const wanted = control.value.trim().toLowerCase();
      if (!wanted) return true;
      const actual = (row.dataset[control.dataset.rosterFilter] || "").toLowerCase();
      return control.dataset.filterMode === "min" ? Number(actual) >= Number(wanted) : actual.includes(wanted);
    });
    row.hidden = !(`${row.dataset.name} ${row.dataset.jobs}`.includes(query) && columnMatch);
  });
  [rosterSearch, ...columnFilters].filter(Boolean).forEach(control => control.addEventListener("input", filterRoster));
  let rosterSort = {key: "name", direction: 1};
  document.querySelectorAll("[data-roster-sort]").forEach(button => button.addEventListener("click", () => {
    const key = button.dataset.rosterSort;
    rosterSort = {key, direction: rosterSort.key === key ? -rosterSort.direction : 1};
    document.querySelectorAll("[data-roster-sort]").forEach(control => {
      control.classList.toggle("active", control === button);
      control.querySelector("span").textContent = control === button ? (rosterSort.direction > 0 ? "ASC" : "DESC") : "Sort";
    });
    const type = button.dataset.sortType;
    const body = document.querySelector("#endgame-roster-body");
    [...body.rows].sort((a, b) => {
      let left = a.dataset[key] || "", right = b.dataset[key] || "";
      if (type === "number") { left = Number(left); right = Number(right); return (left - right) * rosterSort.direction; }
      if (type === "date") { left = Date.parse(left) || 0; right = Date.parse(right) || 0; return (left - right) * rosterSort.direction; }
      return left.localeCompare(right, undefined, {numeric: true}) * rosterSort.direction;
    }).forEach(row => body.appendChild(row));
  }));
  const defaultRosterSort = document.querySelector('[data-roster-sort="name"]');
  if (defaultRosterSort) {
    defaultRosterSort.classList.add("active");
    defaultRosterSort.querySelector("span").textContent = "ASC";
  }
  const lootSearch = document.querySelector("#loot-log-search");
  const lootColumnFilters = [...document.querySelectorAll("[data-loot-filter]")];
  const filterLoot = () => document.querySelectorAll("#loot-log-body tr").forEach(row => {
    const columnMatch = lootColumnFilters.every(control => {
      const wanted = control.value.trim().toLowerCase();
      const actual = (row.dataset[control.dataset.lootFilter] || "").toLowerCase();
      return !wanted || (control.dataset.filterMode === "min" ? Number(actual) >= Number(wanted) : actual.includes(wanted));
    });
    row.hidden = !(row.dataset.search.includes(lootSearch.value.toLowerCase()) && columnMatch);
  });
  [lootSearch, ...lootColumnFilters].filter(Boolean).forEach(control => control.addEventListener("input", filterLoot));
  document.querySelector(".clear-loot-filters")?.addEventListener("click", () => {
    lootColumnFilters.forEach(control => { control.value = ""; });
    lootSearch.value = ""; filterLoot();
  });
  let lootSort = {key: "date", direction: -1};
  document.querySelectorAll("[data-loot-sort]").forEach(button => button.addEventListener("click", () => {
    const key = button.dataset.lootSort;
    lootSort = {key, direction: lootSort.key === key ? -lootSort.direction : 1};
    document.querySelectorAll("[data-loot-sort]").forEach(control => {
      control.classList.toggle("active", control === button);
      control.querySelector("span").textContent = control === button ? (lootSort.direction > 0 ? "ASC" : "DESC") : "Sort";
    });
    const type = button.dataset.sortType;
    const body = document.querySelector("#loot-log-body");
    [...body.rows].sort((a, b) => {
      let left = a.dataset[key] || "", right = b.dataset[key] || "";
      if (type === "date") { left = Date.parse(left) || 0; right = Date.parse(right) || 0; return (left - right) * lootSort.direction; }
      return left.localeCompare(right, undefined, {numeric: true}) * lootSort.direction;
    }).forEach(row => body.appendChild(row));
  }));

  const dialog = document.querySelector("#endgame-dialog"), dialogTitle = document.querySelector("#dialog-title"), dialogContent = document.querySelector("#dialog-content"), dialogEyebrow = document.querySelector("#dialog-eyebrow");
  const auctionDetailDialog = document.querySelector("#auction-detail-dialog");
  const auctionDetailTitle = document.querySelector("#auction-detail-title");
  const auctionDetailContent = document.querySelector("#auction-detail-content");
  const openAuctionDetail = async auctionId => {
    let auction = auctionRecords.get(String(auctionId));
    if (!auction) {
      const response = await fetch("/api/endgame/auctions", {headers: {"Accept": "application/json"}});
      if (!response.ok) return;
      const payload = await response.json();
      auctionRecords = new Map(payload.auctions.map(entry => [String(entry.id), entry]));
      auction = auctionRecords.get(String(auctionId));
    }
    if (!auction || !auctionDetailDialog) return;
    const status = auction.status === "Confirmed" ? "Winners / DKP Completed" : auction.status;
    const members = window.ENDGAME_MEMBERS || [];
    const awardEditor = award => {
      const recipientOptions = members.map(member => `<option value="${member.id}" ${member.id === award.recipient_member_id ? "selected" : ""}>${safeText(member.name)}</option>`).join("");
      const jobOptions = (window.ENDGAME_JOBS || []).map(job => `<option ${job === award.job ? "selected" : ""}>${job}</option>`).join("");
      const priorityOptions = ["P1", "P2", "P3", "Freelot"].map(priority => `<option ${priority === award.distribution ? "selected" : ""}>${priority}</option>`).join("");
      return `<form class="auction-award-editor" method="post" action="/endgame/loot/${award.id}/update" data-auction-id="${auction.id}"><input type="hidden" name="csrf_token" value="${safeText(window.ENDGAME_CSRF)}"><input type="hidden" name="family" value="${safeText(award.family || "Other")}"><input type="hidden" name="classification" value="${safeText(award.classification || "Major Loot")}"><input type="hidden" name="return_to" value="bidding"><label>Item<input name="item" value="${safeText(award.item)}" required></label><label>Recipient<select name="member_id" required>${recipientOptions}</select></label><label>Job<select name="job" required>${jobOptions}</select></label><label>Priority<select name="distribution" required>${priorityOptions}</select></label><label>DKP<input type="number" name="dkp_cost" min="0" max="999" step="1" value="${Number(award.dkp_cost || 0)}" required></label><div><button class="button primary" type="submit">Save Award</button><button class="button danger" type="submit" formaction="/endgame/loot/${award.id}/delete">Remove &amp; Restore DKP</button></div></form>`;
    };
    const items = auction.items.map(item => {
      const bids = item.bids.length ? `<ul>${item.bids.map(bid => `<li><b>${safeText(bid.name)}</b> / ${safeText(bid.job)} / ${bid.amount} DKP / ${bid.tier === 4 ? "Freelot" : `P${bid.tier}`}</li>`).join("")}</ul>` : "<p>No bids were placed.</p>";
      const awards = item.awards?.length ? `<section class="auction-detail-awards"><h4>Confirmed awards</h4>${item.awards.map(award => window.ENDGAME_IS_ADMIN ? awardEditor(award) : `<p><b>${safeText(award.item)}</b> / ${safeText(award.recipient)} / ${award.dkp_cost} DKP</p>`).join("")}</section>` : "";
      return `<article class="auction-detail-item"><h3>${safeText(item.item)}</h3>${item.target_item && item.target_item !== item.item ? `<small>${safeText(item.target_item)}</small>` : ""}${bids}${awards}</article>`;
    }).join("");
    auctionDetailTitle.textContent = `Auction #${auction.id} / ${auction.boss}`;
    auctionDetailContent.innerHTML = `<p class="auction-detail-meta"><b>Event:</b> ${safeText(auction.event_name)} / ${safeText(auction.area)} / ${safeText(status)}</p><div class="auction-detail-items">${items}</div>`;
    if (!auctionDetailDialog.open) auctionDetailDialog.showModal();
  };
  document.querySelector(".auction-detail-close")?.addEventListener("click", () => auctionDetailDialog?.close());
  auctionDetailContent?.addEventListener("submit", async event => {
    const form = event.target.closest(".auction-award-editor");
    if (!form) return;
    event.preventDefault();
    const submitter = event.submitter;
    if (submitter?.formAction?.includes("/delete") && !confirm("Remove this award and restore its DKP to the recipient?")) return;
    const controls = [...form.querySelectorAll("button")];
    controls.forEach(button => { button.disabled = true; });
    try {
      const response = await fetch(submitter?.formAction || form.action, {
        method: "POST", body: new FormData(form), headers: {"Accept": "text/html"}, credentials: "same-origin",
      });
      if (!response.ok) throw new Error("The archived award could not be updated.");
      await loadAuctions();
      await openAuctionDetail(form.dataset.auctionId);
    } catch (error) {
      alert(error.message);
      controls.forEach(button => { button.disabled = false; });
    }
  });
  const eventStoreKey = "hokuten-event-overrides";
  const eventOverrides = JSON.parse(localStorage.getItem(eventStoreKey) || "{}");
  const eventState = button => {
    const date = button.dataset.openEvent;
    if (!eventOverrides[date]) {
      const index = Number(button.dataset.eventIndex);
      eventOverrides[date] = {
        attendees: roster.filter(member => member.attended > index).map(member => member.name),
        loot: loot.filter(row => row.date === date).map(row => ({...row})),
      };
    }
    return eventOverrides[date];
  };
  // Event and loot edits are persisted by the server.  Do not overwrite the
  // server-rendered Linkshell Loot table with the retired browser-only format.
  const syncEventChanges = () => {};
  const saveEventState = () => { localStorage.setItem(eventStoreKey, JSON.stringify(eventOverrides)); syncEventChanges(); };
  const memberOptions = selected => roster.map(member => `<option value="${safeText(member.name)}" ${member.name === selected ? "selected" : ""}>${safeText(member.name)}</option>`).join("");
  const jobOptions = selected => jobs.map(job => `<option value="${job}" ${job === selected ? "selected" : ""}>${job}</option>`).join("");
  const renderEventDetail = eventButton => {
    const date = eventButton.dataset.openEvent;
    const state = eventState(eventButton);
    const attendeeNames = new Set(state.attendees);
    const attendanceRows = window.ENDGAME_IS_ADMIN ? roster : roster.filter(member => attendeeNames.has(member.name));
    const attendanceContent = window.ENDGAME_IS_ADMIN
      ? attendanceRows.map(member => `<div class="event-admin-row"><label><input type="checkbox" data-event-attendee="${safeText(member.name)}" ${attendeeNames.has(member.name) ? "checked" : ""}><b>${safeText(member.name)}</b></label><span>${safeText(member.main_job || "Unassigned")}</span></div>`).join("")
      : attendanceRows.map(member => `<tr><td><b>${safeText(member.name)}</b></td><td>${safeText(member.main_job || "Unassigned")}</td><td><span class="attendance-mark">Attended</span></td></tr>`).join("");
    const lootContent = window.ENDGAME_IS_ADMIN
      ? state.loot.map((row, index) => `<div class="event-loot-editor" data-event-loot-row="${index}"><input name="item" value="${safeText(row.item)}" aria-label="Item"><select name="player" aria-label="Recipient">${memberOptions(row.player)}</select><select name="job" aria-label="Job">${jobOptions(row.job)}</select><select name="award" aria-label="Priority">${["P1","P2","P3","Freelot"].map(value => `<option ${priorityLabel(row.award) === value ? "selected" : ""}>${value}</option>`).join("")}</select><span><button type="button" data-save-event-loot="${index}">Save</button><button class="remove-event-loot" type="button" data-remove-event-loot="${index}">Remove</button></span></div>`).join("")
      : state.loot.map(row => `<tr><td class="event-loot-item"><b>${safeText(row.item)}</b><small>${safeText(row.family)} / ${row.major ? "Major Loot" : "Standard"}</small></td><td>${safeText(row.player)}</td><td><span class="job-badge main">${safeText(row.job)}</span></td><td>${safeText(row.award)}</td></tr>`).join("");
    dialogEyebrow.textContent = `${date} / Endgame event`;
    dialogTitle.textContent = eventButton.dataset.eventName;
    dialogContent.innerHTML = `<div class="event-detail-grid"><section class="event-detail-column"><header><h3>Attendance Roster</h3><span>${state.attendees.length} attended</span></header>${window.ENDGAME_IS_ADMIN ? '<p class="event-admin-note">Check or uncheck a member to update attendance.</p>' : ""}<div class="event-detail-scroll">${window.ENDGAME_IS_ADMIN ? attendanceContent : `<table class="event-detail-table"><thead><tr><th>Member</th><th>Main job</th><th>Status</th></tr></thead><tbody>${attendanceContent}</tbody></table>`}</div></section><section class="event-detail-column"><header><h3>Event Loot</h3><span>${state.loot.length} awards</span></header><div class="event-detail-scroll">${state.loot.length ? (window.ENDGAME_IS_ADMIN ? lootContent : `<table class="event-detail-table"><thead><tr><th>Item</th><th>Recipient</th><th>Job</th><th>Award</th></tr></thead><tbody>${lootContent}</tbody></table>`) : '<p class="event-empty">No loot was recorded for this event.</p>'}</div>${window.ENDGAME_IS_ADMIN ? `<form class="event-add-loot" id="event-add-loot"><input name="item" placeholder="Item name" required><select name="player">${memberOptions("")}</select><select name="job">${jobOptions("")}</select><select name="award"><option>Main priority</option><option>Secondary priority</option><option>Freelot</option></select><select name="major"><option value="major">Major</option><option value="normal">Standard</option></select><button type="submit">Add Drop</button></form>` : ""}</section></div>`;
    if (window.ENDGAME_IS_ADMIN) {
      dialogContent.querySelectorAll("[data-event-attendee]").forEach(control => control.addEventListener("change", () => {
        const name = control.dataset.eventAttendee;
        state.attendees = control.checked ? [...new Set([...state.attendees, name])] : state.attendees.filter(value => value !== name);
        saveEventState(); recordAdminChange("Event Attendance", control.checked ? "Member added" : "Member removed", `${name} / ${date}`); renderEventDetail(eventButton);
      }));
      dialogContent.querySelectorAll("[data-save-event-loot]").forEach(button => button.addEventListener("click", () => {
        const index = Number(button.dataset.saveEventLoot), editor = button.closest("[data-event-loot-row]"), previous = {...state.loot[index]};
        state.loot[index] = {...previous, item: editor.querySelector('[name="item"]').value.trim(), player: editor.querySelector('[name="player"]').value, job: editor.querySelector('[name="job"]').value, award: editor.querySelector('[name="award"]').value};
        saveEventState(); recordAdminChange("Event Loot", "Drop updated", `${previous.item} / ${previous.player} to ${state.loot[index].item} / ${state.loot[index].player} (${date})`); renderEventDetail(eventButton);
      }));
      dialogContent.querySelectorAll("[data-remove-event-loot]").forEach(button => button.addEventListener("click", () => {
        const removed = state.loot.splice(Number(button.dataset.removeEventLoot), 1)[0];
        saveEventState(); recordAdminChange("Event Loot", "Drop removed", `${removed.item} / ${removed.player} (${date})`); renderEventDetail(eventButton);
      }));
      dialogContent.querySelector("#event-add-loot").addEventListener("submit", submitEvent => {
        submitEvent.preventDefault(); const data = new FormData(submitEvent.currentTarget);
        const row = {date, item: data.get("item").trim(), player: data.get("player"), job: data.get("job"), award: data.get("award"), major: data.get("major") === "major", family: "Other"};
        state.loot.push(row); saveEventState(); recordAdminChange("Event Loot", "Drop added", `${row.item} / ${row.player} (${date})`); renderEventDetail(eventButton);
      });
    }
    dialog.classList.add("event-detail-dialog");
    if (!dialog.open) dialog.showModal();
  };
  syncEventChanges();
  dialog.addEventListener("close", () => dialog.classList.remove("event-detail-dialog", "member-history-dialog"));
  document.querySelector(".dialog-close").addEventListener("click", () => { dialog.close(); dialog.classList.remove("event-detail-dialog", "member-history-dialog"); });
  document.addEventListener("click", event => {
    const auctionLink = event.target.closest("[data-open-auction]");
    const memberCell = event.target.closest("#endgame-roster-body td:first-child");
    const eventHistoryLink = event.target.closest("[data-member-event-link]");
    const lootHistoryLink = event.target.closest("[data-member-loot-link]");
    const serverEventButton = event.target.closest("[data-open-server-event]");
    const attendanceEditButton = event.target.closest("[data-edit-attendance]");
    const eventButton = event.target.closest("[data-open-event]");
    const jobBadge = event.target.closest("[data-job-member]");
    const attendance = event.target.closest("[data-attendance]"); const wins = event.target.closest("[data-wins]");
    if (auctionLink) {
      event.preventDefault();
      openAuctionDetail(auctionLink.dataset.openAuction);
      return;
    }
    if (lootHistoryLink) {
      const eventId = lootHistoryLink.dataset.memberLootLink;
      dialog.close();
      document.querySelector(`[data-open-server-event="${eventId}"]`)?.click();
      return;
    }
    if (eventHistoryLink) {
      dialog.close();
      activateView("event-calendar");
      const card = document.querySelector(`#guild-event-${eventHistoryLink.dataset.memberEventLink}`);
      if (card) { card.open = true; card.scrollIntoView({behavior: "smooth", block: "start"}); }
      return;
    }
    if (memberCell) {
      const rosterMember = roster.find(row => row.name.toLowerCase() === memberCell.closest("tr").dataset.name);
      const member = rosterMember ? (window.ENDGAME_MEMBER_DETAILS || {})[String(rosterMember.id)] : null;
      if (!member) return;
      const eventRows = member.events.map(row => {
        const positive = row.is_upcoming ? row.signed_up : row.attended;
        const status = row.is_upcoming
          ? (row.signed_up ? "✓ Signed Up" : "✕ Not Signed Up")
          : (row.attended ? "✓ Attended" : "✕ Not Attended");
        return `<tr><td><button class="member-event-link" type="button" data-member-event-link="${row.id}">${safeText(row.start_at.slice(0,10))}<small>${safeText(row.name)}</small></button></td><td><span class="attendance-result ${positive ? "attended" : "missed"}">${status}</span></td></tr>`;
      }).join("");
      const lootRows = member.loot.map(row => `<tr><td><button class="member-loot-link" type="button" data-member-loot-link="${row.event_id}"><b>${safeText(row.item)}</b><small>${safeText(priorityLabel(row.award))}</small></button></td><td><button class="member-event-link" type="button" data-member-event-link="${row.event_id}">${safeText(row.event_date)}<small>${safeText(row.event_name)}</small></button>${row.auction_id ? `<button class="member-auction-link" type="button" data-open-auction="${row.auction_id}">Auction #${row.auction_id}</button>` : ""}</td><td>${Number(row.dkp_cost || 0)} DKP</td></tr>`).join("");
      dialogEyebrow.textContent = "Member event and award history";
      dialogTitle.textContent = member.name;
      const completedEvents = member.events.filter(row => !row.is_upcoming);
      dialogContent.innerHTML = `<div class="member-history-summary dkp-member-summary"><span>DKP balance <b>${member.dkp}</b></span><span>Total spent <b>${member.total_spent}</b></span><span>Lifetime earned <b>${member.lifetime_earned}</b></span><span>Last event <b>${safeText(member.last_event)}</b></span><span>Dynamis lots <b>${safeText(member.dynamis_main || "—")} / ${safeText(member.dynamis_secondary || "—")}</b></span></div><section class="member-history-section"><header><h3>Event Attendance</h3><span>${completedEvents.filter(row => row.attended).length}/${completedEvents.length} attended</span></header><div class="endgame-table-wrap"><table class="endgame-table member-history-table"><thead><tr><th>Event</th><th>Status</th></tr></thead><tbody>${eventRows}</tbody></table></div></section><section class="member-history-section"><header><h3>Loot Wins</h3><span>${member.loot.length} awards</span></header><div class="endgame-table-wrap">${lootRows ? `<table class="endgame-table member-history-table"><thead><tr><th>Item</th><th>Event</th><th>DKP spent</th></tr></thead><tbody>${lootRows}</tbody></table>` : '<p class="event-empty">No loot wins recorded.</p>'}</div></section>`;
      dialog.classList.add("member-history-dialog");
      dialog.showModal();
      return;
    }
    if (serverEventButton) {
      const selected = (window.ENDGAME_EVENTS || []).find(row => String(row.id) === serverEventButton.dataset.openServerEvent);
      if (!selected) return;
      const attendees = selected.attendees || [];
      const awards = selected.loot || [];
      const eventAuctions = selected.auctions || [];
      const auctionArchive = eventAuctions.length ? `<section class="event-auction-archive"><header><h3>Event Auctions</h3><span>${eventAuctions.length} auction${eventAuctions.length === 1 ? "" : "s"}</span></header>${eventAuctions.map(auction => `<button class="event-auction-link ${auction.status === "Confirmed" ? "completed" : ""}" type="button" data-open-auction="${auction.id}"><b>Auction #${auction.id} / ${safeText(auction.boss)}</b><span>${safeText(auction.area)} · ${safeText(auction.status === "Confirmed" ? "Winners / DKP Completed" : auction.status)}${auction.award_count ? ` · ${auction.award_count} awards` : ""}</span></button>`).join("")}</section>` : "";
      const allMembers = window.ENDGAME_MEMBERS || [];
      const lootCatalog = window.ENDGAME_LOOT_CATALOG || [];
      const lootOptions = `<option value="">Select Sky or Sea item</option>${lootCatalog.map(item => `<option value="${safeText(item.name)}" data-family="${safeText(item.family)}">${safeText(item.area)} · ${safeText(item.source)} · ${safeText(item.name)}</option>`).join("")}`;
      const csrf = safeText(document.querySelector('input[name="csrf_token"]')?.value || window.ENDGAME_CSRF || "");
      const lootPanel = window.ENDGAME_IS_ADMIN
        ? awards.map(row => `<form method="post" action="/endgame/loot/${row.id}/update" class="event-loot-persistent-editor"><input type="hidden" name="csrf_token" value="${csrf}"><input type="hidden" name="family" value="${safeText(row.family || "Other")}"><input type="hidden" name="classification" value="Major Loot"><input name="item" value="${safeText(row.item)}" aria-label="Item"><select name="member_id" aria-label="Recipient">${allMembers.map(member => `<option value="${member.id}" ${member.name === row.player ? "selected" : ""}>${safeText(member.name)}</option>`).join("")}</select><select name="job" aria-label="Receiving job">${jobs.map(job => `<option ${job === row.job ? "selected" : ""}>${job}</option>`).join("")}</select><select name="distribution" aria-label="Priority">${["P1","P2","P3","Freelot"].map(value => `<option ${priorityLabel(row.award) === value ? "selected" : ""}>${value}</option>`).join("")}</select><input type="number" name="dkp_cost" min="0" max="999" step="1" value="${Number(row.dkp_cost || 0)}" aria-label="DKP spent"><div><button type="submit">Save</button><button class="danger" type="submit" formaction="/endgame/loot/${row.id}/delete">Remove &amp; Restore DKP</button></div></form>`).join("") || '<p class="event-empty">No loot was recorded for this event.</p>'
        : awards.length ? `<table class="event-detail-table"><thead><tr><th>Item</th><th>Recipient</th><th>Job</th><th>Priority</th><th>DKP</th></tr></thead><tbody>${awards.map(row => `<tr><td class="event-loot-item"><b>${safeText(row.item)}</b></td><td>${safeText(row.player)}</td><td><span class="job-badge main">${safeText(row.job)}</span></td><td>${safeText(priorityLabel(row.award))}</td><td>${Number(row.dkp_cost || 0)}</td></tr>`).join("")}</tbody></table>` : '<p class="event-empty">No loot was recorded for this event.</p>';
      const manualLootForm = window.ENDGAME_IS_ADMIN ? `<form method="post" action="/endgame/loot" class="event-add-loot persistent-event-add"><input type="hidden" name="csrf_token" value="${csrf}"><input type="hidden" name="event_id" value="${selected.id}"><input type="hidden" name="classification" value="Major Loot"><h4>Add Loot Drop</h4><select name="item" required>${lootOptions}</select><select name="member_id" required><option value="">Recipient</option>${allMembers.map(member => `<option value="${member.id}">${safeText(member.name)}</option>`).join("")}</select><select name="job" required><option value="">Job</option>${jobs.map(job => `<option>${job}</option>`).join("")}</select><select name="distribution"><option>P1</option><option>P2</option><option>P3</option><option selected>Freelot</option></select><input type="number" name="dkp_cost" min="0" max="999" step="1" value="0" aria-label="DKP spent"><button class="button primary" type="submit">Add Loot Drop</button></form>` : "";
      dialogEyebrow.textContent = `${selected.start_at.slice(0, 10)} / Endgame event`;
      dialogTitle.textContent = `${selected.name} / Loot`;
      dialogContent.innerHTML = `<section class="event-detail-column event-loot-only"><header><h3>Event Loot</h3><span>${awards.length} awards</span></header><div class="event-detail-scroll">${lootPanel}</div>${manualLootForm}</section>`;
      dialogContent.insertAdjacentHTML("beforeend", auctionArchive);
      dialog.classList.add("event-detail-dialog");
      dialog.showModal();
      return;
    }
    if (attendanceEditButton && window.ENDGAME_IS_ADMIN) {
      const selected = (window.ENDGAME_EVENTS || []).find(row => String(row.id) === attendanceEditButton.dataset.editAttendance);
      if (!selected) return;
      const attendeeIds = new Set((selected.attendees || []).map(member => Number(member.id)));
      const allMembers = window.ENDGAME_MEMBERS || [];
      const csrf = safeText(document.querySelector('input[name="csrf_token"]')?.value || window.ENDGAME_CSRF || "");
      dialogEyebrow.textContent = `${selected.start_at.slice(0, 10)} / Administrator attendance`;
      dialogTitle.textContent = `${selected.name} / Attendance`;
      dialogContent.innerHTML = `<form method="post" action="/endgame/events/${selected.id}/attendance" class="event-attendance-editor"><input type="hidden" name="csrf_token" value="${csrf}"><div class="event-attendance-checks">${allMembers.map(member => `<label><input type="checkbox" name="member_ids" value="${member.id}" ${attendeeIds.has(Number(member.id)) ? "checked" : ""}><span>${safeText(member.name)}</span></label>`).join("")}</div><div class="attendance-editor-actions"><button class="button primary" type="submit">Save Attendance</button><button class="button edit-attendance-button" type="button" data-cancel-attendance>Cancel</button></div></form>`;
      dialogContent.querySelector("[data-cancel-attendance]").addEventListener("click", () => dialog.close());
      dialog.showModal();
      return;
    }
    if (eventButton) { renderEventDetail(eventButton); return; }
    if (eventButton) {
      const eventIndex = Number(eventButton.dataset.eventIndex);
      const attendees = roster.filter(member => member.attended > eventIndex);
      const eventLoot = loot.filter(row => row.date === eventButton.dataset.openEvent);
      dialogEyebrow.textContent = `${eventButton.dataset.openEvent} / Endgame event`;
      dialogTitle.textContent = eventButton.dataset.eventName;
      dialogContent.innerHTML = `<div class="event-detail-grid"><section class="event-detail-column"><header><h3>Attendance Roster</h3><span>${attendees.length} attended</span></header><div class="event-detail-scroll"><table class="event-detail-table"><thead><tr><th>Member</th><th>Main job</th><th>Status</th></tr></thead><tbody>${attendees.map(member => `<tr><td><b>${member.name}</b></td><td>${member.main_job || "Unassigned"}</td><td><span class="attendance-mark">Attended</span></td></tr>`).join("")}</tbody></table></div></section><section class="event-detail-column"><header><h3>Event Loot</h3><span>${eventLoot.length} awards</span></header><div class="event-detail-scroll">${eventLoot.length ? `<table class="event-detail-table"><thead><tr><th>Item</th><th>Recipient</th><th>Job</th><th>Award</th></tr></thead><tbody>${eventLoot.map(row => `<tr><td class="event-loot-item"><b>${row.item}</b><small>${row.family} / ${row.major ? "Major Loot" : "Standard"}</small></td><td>${row.player}</td><td><span class="job-badge main">${row.job}</span></td><td>${row.award}</td></tr>`).join("")}</tbody></table>` : '<p class="event-empty">No loot was recorded for this event.</p>'}</div></section></div>`;
      dialog.classList.add("event-detail-dialog");
      dialog.showModal();
    }
    if (jobBadge && window.ENDGAME_IS_ADMIN) {
      const member = roster.find(row => row.name === jobBadge.dataset.jobMember);
      const slot = jobBadge.dataset.jobSlot;
      const slotLabel = slot === "main_job" ? "Main Job" : "Secondary Job";
      dialogEyebrow.textContent = "Administrator job registration";
      dialogTitle.textContent = `${member.name} / ${slotLabel}`;
      dialogContent.innerHTML = `<form class="job-change-form" id="job-change-form"><p class="job-change-help">Saving this selection adds a timestamped entry to the badge's hover history.</p><label>${slotLabel}<select name="job"><option value="">Unassigned</option>${jobs.map(job => `<option value="${job}" ${job === member[slot] ? "selected" : ""}>${job}</option>`).join("")}</select></label><button type="submit">Save Job Change</button></form>`;
      dialogContent.querySelector("form").addEventListener("submit", submitEvent => {
        submitEvent.preventDefault();
        const nextJob = new FormData(submitEvent.currentTarget).get("job");
        const otherSlot = slot === "main_job" ? "secondary_job" : "main_job";
        if (nextJob && nextJob === member[otherSlot]) {
          dialogContent.querySelector(".job-change-help").textContent = `${nextJob} is already registered in the other priority slot.`;
          return;
        }
        const previousJob = member[slot] || "";
        if (nextJob === previousJob) { dialog.close(); return; }
        const entry = {member: member.name, slot, from: previousJob, to: nextJob, at: new Date().toLocaleString(), actor: window.ENDGAME_ACTOR || "Administrator"};
        jobChanges.push(entry);
        localStorage.setItem(jobChangeKey, JSON.stringify(jobChanges));
        recordAdminChange("Job Selections", `${slotLabel} changed`, `${member.name}: ${previousJob || "Unassigned"} to ${nextJob || "Unassigned"}`);
        updateJobDisplay(member.name, slot, nextJob);
        rankMatrixPriority();
        filterRoster();
        dialog.close();
      });
      dialog.showModal();
    }
    if (attendance) { const member = roster.find(row => row.name === attendance.dataset.attendance); dialogEyebrow.textContent = "Rolling attendance detail"; dialogTitle.textContent = member.name; dialogContent.innerHTML = `<div class="dialog-list"><article><div><b>Imported Event 02</b><small>Individual event detail pending import</small></div><span>${member.attended === 2 ? "Attended" : "Review"}</span></article><article><div><b>Imported Event 01</b><small>Individual event detail pending import</small></div><span>${member.attended ? "Attended / review" : "Missed"}</span></article></div>`; dialog.showModal(); }
    if (wins) { const rows = loot.filter(row => row.player === wins.dataset.wins); dialogEyebrow.textContent = "Loot history"; dialogTitle.textContent = wins.dataset.wins; dialogContent.innerHTML = rows.length ? `<div class="dialog-list">${rows.map(row => `<article><div><b>${row.item}</b><small>${row.date} · ${row.job} · ${row.award}</small></div><span>${row.major ? "Major" : "Standard"}</span></article>`).join("")}</div>` : "<p>No awards are recorded for this member.</p>"; dialog.showModal(); }
  });

  const priorityMatrixDialog = document.querySelector("#priority-matrix-dialog");
  document.querySelector("#open-priority-matrix")?.addEventListener("click", () => priorityMatrixDialog.showModal());
  priorityMatrixDialog?.querySelector(".priority-dialog-close")?.addEventListener("click", () => priorityMatrixDialog.close());
  priorityMatrixDialog?.addEventListener("click", event => {
    if (event.target === priorityMatrixDialog) priorityMatrixDialog.close();
  });

  const recordLootDialog = document.querySelector("#record-loot-dialog");
  const recordLootItem = document.querySelector("#record-loot-item");
  const recordLootMember = document.querySelector("#record-loot-member");
  const recordLootJob = document.querySelector("#record-loot-job");
  const updateLootDefaults = () => {
    if (!recordLootDialog) return;
    document.querySelector("#record-loot-family").value = recordLootItem.selectedOptions[0]?.dataset.family || "";
    const member = roster.find(row => String(row.id) === recordLootMember.value);
    const job = recordLootJob.value;
    document.querySelector("#record-loot-distribution").value = member && job === member.main_job
      ? "Main priority"
      : member && job === member.secondary_job ? "Secondary priority" : "Freelot";
  };
  document.querySelector("#open-record-loot")?.addEventListener("click", () => recordLootDialog.showModal());
  recordLootDialog?.querySelector(".record-loot-close")?.addEventListener("click", () => recordLootDialog.close());
  [recordLootItem, recordLootMember, recordLootJob].filter(Boolean).forEach(control => control.addEventListener("change", updateLootDefaults));

  if (false) { // Linkshell Pops now runs in its own isolated script below the dashboard.
  let popArea = "Sky";
  const popItems = window.POP_ITEMS || [], popTargets = window.POP_TARGETS || [];
  let saved = {};
  const holder = document.querySelector("#pop-holder");
  const quantity = (name, key) => Number(saved[name]?.[key] || 0);
  const totals = () => Object.keys(saved).reduce((result, name) => { Object.entries(saved[name]).forEach(([key, value]) => result[key] = (result[key] || 0) + Number(value)); return result; }, {});
  const renderPops = () => {
    const aggregate = totals(), areaItems = popItems.filter(item => item.area === popArea);
    document.querySelector("#pop-inventory").innerHTML = areaItems.map(item => { const owners = Object.keys(saved).filter(name => quantity(name, item.key) > 0); return `<article class="pop-item"><div><b>${item.name}</b><small>${item.source}${item.bundle ? ` · ${item.bundle} required per pop` : ""}</small></div><div class="quantity-stepper"><button data-pop-change="-1" data-key="${item.key}">−</button><b>${quantity(holder.value,item.key)}</b><button data-pop-change="1" data-key="${item.key}">+</button></div><span class="holder-list">Linkshell total: <b>${aggregate[item.key] || 0}</b>${owners.length ? ` · Held by ${owners.join(", ")}` : " · No recorded holders"}</span></article>`; }).join("");
    const targets = popTargets.filter(target => target.area === popArea); let ready = 0;
    document.querySelector("#pop-readiness").innerHTML = targets.map(target => { const requirements = target.requires.map(raw => { const [key, amountRaw] = raw.split(":"); const amount = Number(amountRaw || 1), held = aggregate[key] || 0; return {key, amount, held, met: held >= amount, item: popItems.find(item => item.key === key)}; }); const complete = requirements.every(req => req.met); if (complete) ready += 1; const sets = Math.min(...requirements.map(req => Math.floor(req.held / req.amount))); return `<article class="pop-target ${complete ? "ready" : "partial"}"><header><h4>${target.name}</h4><span class="readiness-badge">${complete ? `${sets} pop${sets === 1 ? "" : "s"} ready` : "Components needed"}</span></header><div class="requirement-list">${requirements.map(req => `<span class="${req.met ? "have" : ""}">${req.item.name} ${req.held}/${req.amount}</span>`).join("")}</div></article>`; }).join("");
    document.querySelector("#pop-component-count").textContent = `${areaItems.reduce((sum,item) => sum + (aggregate[item.key] || 0),0)} components held`; document.querySelector("#pop-ready-count").textContent = `${ready} ready`;
  };
  document.querySelectorAll("[data-pop-area]").forEach(button => button.addEventListener("click", () => { popArea = button.dataset.popArea; document.querySelectorAll("[data-pop-area]").forEach(row => row.classList.toggle("active", row === button)); renderPops(); }));
  holder.addEventListener("change", renderPops);
  const loadPops = async () => {
    try {
      const response = await fetch("/api/endgame/pops", {headers: {Accept: "application/json"}});
      if (!response.ok) throw new Error();
      saved = (await response.json()).inventory || {};
    } catch (_) { saved = {}; }
    renderPops();
  };
  document.querySelector("#pop-inventory").addEventListener("click", async event => {
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
      renderPops();
    } catch (error) { alert(error.message); button.disabled = false; }
  });
  // Render the complete Sky list immediately; shared quantities hydrate right after.
  // This keeps all pop requirements usable even if the inventory request is delayed.
  renderPops();
  loadPops();
  }
})();
