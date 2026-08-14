(() => {
  const tabs = [...document.querySelectorAll("[data-endgame-tab]")];
  const panels = [...document.querySelectorAll("[data-endgame-panel]")];
  const viewTabs = [...document.querySelectorAll("[data-endgame-view]")];
  const viewPanels = [...document.querySelectorAll("[data-endgame-view-panel]")];
  const activateView = name => {
    viewTabs.forEach(tab => tab.classList.toggle("active", tab.dataset.endgameView === name));
    viewPanels.forEach(panel => { panel.hidden = panel.dataset.endgameViewPanel !== name; });
  };
  viewTabs.forEach(tab => tab.addEventListener("click", () => {
    const name = tab.dataset.endgameView; activateView(name);
    history.replaceState(null, "", name === "event-calendar" ? "#event-calendar" : "#priority");
  }));
  const activate = name => {
    tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.endgameTab === name));
    panels.forEach(panel => { const active = panel.dataset.endgamePanel === name; panel.hidden = !active; panel.classList.toggle("active", active); });
    history.replaceState(null, "", `#${name}`);
  };
  tabs.forEach(tab => tab.addEventListener("click", () => activate(tab.dataset.endgameTab)));
  const requested = location.hash.slice(1);
  if (tabs.some(tab => tab.dataset.endgameTab === requested)) { activateView("operations"); activate(requested); }
  else activateView("event-calendar");
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
  const loot = window.ENDGAME_LOOT || [];
  const priorityItems = window.ENDGAME_PRIORITY_ITEMS || [];
  const jobs = window.ENDGAME_JOBS || [];
  const jobChangeKey = "hokuten-job-change-log";
  const jobChanges = JSON.parse(localStorage.getItem(jobChangeKey) || "[]");
  const adminAuditKey = "hokuten-admin-audit";
  const adminAudit = [...(window.ENDGAME_SERVER_AUDIT || []), ...JSON.parse(localStorage.getItem(adminAuditKey) || "[]")];
  const safeText = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[character]));
  const renderAdminAudit = () => {
    const body = document.querySelector("#admin-audit-body");
    if (!body) return;
    body.innerHTML = adminAudit.length ? adminAudit.slice().reverse().map(row => `<tr><td>${safeText(row.at)}</td><td><b>${safeText(row.actor)}</b></td><td>${safeText(row.area)}</td><td>${safeText(row.action)}</td><td>${safeText(row.details)}</td></tr>`).join("") : '<tr><td colspan="5">No administrator changes have been recorded in this browser yet.</td></tr>';
  };
  const recordAdminChange = (area, action, details) => {
    adminAudit.push({at: new Date().toLocaleString(), actor: window.ENDGAME_ACTOR || "Administrator", area, action, details});
    localStorage.setItem(adminAuditKey, JSON.stringify(adminAudit));
    renderAdminAudit();
  };
  renderAdminAudit();
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
      document.querySelector("#priority-family").value = "";
      document.querySelector("#priority-title").textContent = "Select an item";
      document.querySelector("#priority-note").textContent = "Source, item family, job tiers, and calculated priority will appear automatically.";
      document.querySelector("#priority-tiers").innerHTML = "";
      priorityBody.innerHTML = '<tr><td colspan="8">Select a Sky or Sea drop to calculate priority.</td></tr>';
      return;
    }
    const major = priorityMajor.value === "major";
    const tierFor = job => item.freelot ? 4 : item.p1.includes(job) ? 1 : item.p2.includes(job) ? 2 : item.p3.includes(job) ? 3 : 99;
    const candidates = roster.map(member => {
      const mainTier = tierFor(member.main_job), secondaryTier = tierFor(member.secondary_job);
      const useMain = mainTier <= secondaryTier;
      return {...member, priorityTier: Math.min(mainTier, secondaryTier), jobStatus: useMain ? 1 : 2, eligibleJob: useMain ? member.main_job : member.secondary_job};
    }).filter(member => member.priorityTier < 99 && (item.freelot || member.eligibleJob))
      .sort((a, b) => a.priorityTier - b.priorityTier || a.jobStatus - b.jobStatus || a.tier - b.tier || (major ? Number(a.cooldown) - Number(b.cooldown) : 0) || a.major_wins - b.major_wins || lastDate(a.last_major_win) - lastDate(b.last_major_win) || a.name.localeCompare(b.name));
    document.querySelector("#priority-source").value = `${item.area} / ${item.source}`;
    document.querySelector("#priority-family").value = item.family;
    document.querySelector("#priority-title").textContent = `${item.name} / ${item.source}`;
    document.querySelector("#priority-note").textContent = candidates.length ? `${candidates.length} registered candidates ranked from the supplied job-priority matrix.` : "No member has an eligible registered job for this item.";
    document.querySelector("#priority-tiers").innerHTML = item.freelot ? '<article class="freelot"><span>Distribution</span><b>Freelot</b><small>Attendance and general eligibility still apply.</small></article>' : [1,2,3].map(tier => `<article><span>P${tier}</span><b>${(item[`p${tier}`] || []).join(" / ") || "None"}</b><small>${tier === 1 ? "First consideration" : tier === 2 ? "After eligible P1 jobs" : "After eligible P1 and P2 jobs"}</small></article>`).join("");
    priorityBody.innerHTML = candidates.map((member, index) => {
      const label = item.freelot ? "Freelot" : `P${member.priorityTier}`;
      const explanation = item.freelot ? `Freelot / Tier ${member.tier} attendance` : `${label} ${member.eligibleJob} / ${member.jobStatus === 1 ? "Main" : "Secondary"} registration`;
      return `<tr><td><span class="rank-number ${index === 0 ? "top" : ""}">${index + 1}</span></td><td><b>${member.name}</b></td><td><span class="job-badge ${member.jobStatus === 1 ? "main" : ""}">${label} / ${member.jobStatus === 1 ? "Main" : "Secondary"} ${member.eligibleJob || ""}</span></td><td><span class="tier tier-${member.tier}">Tier ${member.tier} / ${member.attendance}%</span></td><td><span class="cooldown ${member.cooldown ? "locked" : "ready"}">${member.cooldown ? "Cooldown" : "Ready"}</span></td><td>${member.major_wins}</td><td>${member.last_major_win}</td><td><small>${explanation}</small></td></tr>`;
    }).join("") || '<tr><td colspan="8">No eligible registered members for this item.</td></tr>';
  };
  [priorityItem, priorityMajor].forEach(control => control.addEventListener("input", rankMatrixPriority));
  rankMatrixPriority();

  const rosterSearch = document.querySelector("#endgame-roster-search");
  const tierFilter = document.querySelector("#endgame-tier-filter");
  const columnFilters = [...document.querySelectorAll("[data-roster-filter]")];
  const filterRoster = () => document.querySelectorAll("#endgame-roster-body tr").forEach(row => {
    const query = rosterSearch.value.toLowerCase();
    const columnMatch = columnFilters.every(control => {
      const wanted = control.value.trim().toLowerCase();
      if (!wanted) return true;
      const actual = (row.dataset[control.dataset.rosterFilter] || "").toLowerCase();
      return control.dataset.filterMode === "min" ? Number(actual) >= Number(wanted) : actual.includes(wanted);
    });
    row.hidden = !(`${row.dataset.name} ${row.dataset.jobs}`.includes(query) && (!tierFilter.value || row.dataset.tier === tierFilter.value) && columnMatch);
  });
  [rosterSearch, tierFilter, ...columnFilters].forEach(control => control.addEventListener("input", filterRoster));
  document.querySelector(".clear-roster-filters").addEventListener("click", () => {
    columnFilters.forEach(control => { control.value = ""; });
    rosterSearch.value = ""; tierFilter.value = ""; filterRoster();
  });
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
  const lootSearch = document.querySelector("#loot-log-search"), lootMajor = document.querySelector("#loot-major-filter");
  const lootColumnFilters = [...document.querySelectorAll("[data-loot-filter]")];
  const filterLoot = () => document.querySelectorAll("#loot-log-body tr").forEach(row => {
    const columnMatch = lootColumnFilters.every(control => {
      const wanted = control.value.trim().toLowerCase();
      return !wanted || (row.dataset[control.dataset.lootFilter] || "").includes(wanted);
    });
    row.hidden = !(row.dataset.search.includes(lootSearch.value.toLowerCase()) && (!lootMajor.value || row.dataset.major === lootMajor.value) && columnMatch);
  });
  [lootSearch, lootMajor, ...lootColumnFilters].forEach(control => control.addEventListener("input", filterLoot));
  document.querySelector(".clear-loot-filters").addEventListener("click", () => {
    lootColumnFilters.forEach(control => { control.value = ""; });
    lootSearch.value = ""; lootMajor.value = ""; filterLoot();
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
  const syncEventChanges = () => {
    const overriddenDates = new Set(Object.keys(eventOverrides));
    const currentLoot = [...loot.filter(row => !overriddenDates.has(row.date)), ...Object.values(eventOverrides).flatMap(state => state.loot)];
    const body = document.querySelector("#loot-log-body");
    body.innerHTML = currentLoot.map(row => `<tr data-search="${safeText(`${row.item} ${row.player} ${row.job} ${row.family} ${row.award}`.toLowerCase())}" data-date="${safeText(row.date.toLowerCase())}" data-item="${safeText(row.item.toLowerCase())}" data-recipient="${safeText(row.player.toLowerCase())}" data-job="${safeText(row.job.toLowerCase())}" data-family="${safeText((row.family || "Other").toLowerCase())}" data-award="${safeText(row.award.toLowerCase())}" data-major="${row.major ? "major" : "normal"}"><td>${safeText(row.date)}</td><td><b>${safeText(row.item)}</b></td><td>${safeText(row.player)}</td><td><span class="job-badge main">${safeText(row.job)}</span></td><td>${safeText(row.family || "Other")}</td><td>${safeText(row.award)}</td><td><span class="loot-class ${row.major ? "major" : "normal"}">${row.major ? "Major Loot" : "Standard"}</span></td></tr>`).join("");
    document.querySelectorAll("[data-open-event]").forEach(button => {
      const state = eventOverrides[button.dataset.openEvent]; if (!state) return;
      const meta = button.closest(".event-card").querySelector(".event-meta");
      meta.querySelector("b").textContent = `${state.loot.length} loot awards`;
      meta.querySelector("span").textContent = `${state.attendees.length} attended`;
    });
  };
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
      ? state.loot.map((row, index) => `<div class="event-loot-editor" data-event-loot-row="${index}"><input name="item" value="${safeText(row.item)}" aria-label="Item"><select name="player" aria-label="Recipient">${memberOptions(row.player)}</select><select name="job" aria-label="Job">${jobOptions(row.job)}</select><select name="award" aria-label="Distribution"><option ${row.award === "Main priority" ? "selected" : ""}>Main priority</option><option ${row.award === "Secondary priority" ? "selected" : ""}>Secondary priority</option><option ${row.award === "Freelot" ? "selected" : ""}>Freelot</option></select><select name="major" aria-label="Classification"><option value="major" ${row.major ? "selected" : ""}>Major</option><option value="normal" ${!row.major ? "selected" : ""}>Standard</option></select><span><button type="button" data-save-event-loot="${index}">Save</button><button class="remove-event-loot" type="button" data-remove-event-loot="${index}">Remove</button></span></div>`).join("")
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
        state.loot[index] = {...previous, item: editor.querySelector('[name="item"]').value.trim(), player: editor.querySelector('[name="player"]').value, job: editor.querySelector('[name="job"]').value, award: editor.querySelector('[name="award"]').value, major: editor.querySelector('[name="major"]').value === "major"};
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
  dialog.addEventListener("close", () => dialog.classList.remove("event-detail-dialog"));
  document.querySelector(".dialog-close").addEventListener("click", () => { dialog.close(); dialog.classList.remove("event-detail-dialog"); });
  document.addEventListener("click", event => {
    const eventButton = event.target.closest("[data-open-event]");
    const jobBadge = event.target.closest("[data-job-member]");
    const attendance = event.target.closest("[data-attendance]"); const wins = event.target.closest("[data-wins]");
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

  let popArea = "Sky";
  const popItems = window.POP_ITEMS || [], popTargets = window.POP_TARGETS || [];
  const saved = JSON.parse(localStorage.getItem("hokuten-pop-prototype") || "{}");
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
  document.querySelector("#pop-inventory").addEventListener("click", event => { const button = event.target.closest("[data-pop-change]"); if (!button) return; saved[holder.value] ||= {}; saved[holder.value][button.dataset.key] = Math.max(0, quantity(holder.value, button.dataset.key) + Number(button.dataset.popChange)); localStorage.setItem("hokuten-pop-prototype", JSON.stringify(saved)); renderPops(); });
  renderPops();
})();
