(() => {
  const transitions = {
    Light:{Light:[4,"Light","Radiance"]}, Darkness:{Darkness:[4,"Darkness","Umbra"]},
    Gravitation:{Distortion:[3,"Darkness"],Fragmentation:[2,"Fragmentation"]}, Fragmentation:{Fusion:[3,"Light"],Distortion:[2,"Distortion"]},
    Distortion:{Gravitation:[3,"Darkness"],Fusion:[2,"Fusion"]}, Fusion:{Fragmentation:[3,"Light"],Gravitation:[2,"Gravitation"]},
    Compression:{Transfixion:[1,"Transfixion"],Detonation:[1,"Detonation"]}, Liquefaction:{Impaction:[2,"Fusion"],Scission:[1,"Scission"]},
    Induration:{Reverberation:[2,"Fragmentation"],Compression:[1,"Compression"],Impaction:[1,"Impaction"]}, Reverberation:{Induration:[1,"Induration"],Impaction:[1,"Impaction"]},
    Transfixion:{Scission:[2,"Distortion"],Reverberation:[1,"Reverberation"],Compression:[1,"Compression"]}, Scission:{Liquefaction:[1,"Liquefaction"],Reverberation:[1,"Reverberation"],Detonation:[1,"Detonation"]},
    Detonation:{Compression:[2,"Gravitation"],Scission:[1,"Scission"]}, Impaction:{Liquefaction:[1,"Liquefaction"],Detonation:[1,"Detonation"]}
  };
  const burstElements = {Liquefaction:["Fire"],Induration:["Ice"],Detonation:["Wind"],Scission:["Earth"],Reverberation:["Water"],Impaction:["Lightning"],Transfixion:["Light"],Compression:["Dark"],Fusion:["Fire","Light"],Fragmentation:["Wind","Lightning"],Distortion:["Ice","Water"],Gravitation:["Earth","Dark"],Light:["Fire","Wind","Lightning","Light"],Darkness:["Earth","Water","Ice","Dark"],Radiance:["Light"],Umbra:["Dark"]};
  const party = document.querySelector("#skillchain-party"), output = document.querySelector("#skillchain-output"), count = document.querySelector("#skillchain-count"), summary = document.querySelector("#skillchain-summary"), toggleGroups = document.querySelector("#skillchain-toggle-groups"), requireWeaponSkillFirst = document.querySelector("#require-weaponskill-first"), typeFilter = document.querySelector("#skillchain-type-filter");
  let catalog, players = Array.from({length:4}, () => ({job:"",weapon:"",preferred:"",level:75}));
  const syncGroupButton = () => { const groups=[...output.querySelectorAll(".skillchain-group")]; toggleGroups.disabled=!groups.length; toggleGroups.textContent=groups.some(group => group.open) ? "Collapse all" : "Expand all"; };
  toggleGroups.addEventListener("click", () => { const groups=[...output.querySelectorAll(".skillchain-group")], open=groups.some(group => group.open); groups.forEach(group => { group.open=!open; }); syncGroupButton(); });
  const escape = value => String(value).replace(/[&<>"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
  const availableAtLevel = (action, player) => { const level=Number(player.level); if (!Number.isInteger(level) || level < 1 || level > 75) return false; if (action.level_requirement) return action.level_requirement <= level; const rank=action.skill_ranks?.[player.job]; return Boolean(rank && catalog.skill_caps[String(level)]?.[String(rank)] >= action.skill_level); };
  const actionsFor = player => !player.job || !player.weapon ? [] : catalog.actions.filter(action => action.jobs.includes(player.job) && action.weapon === player.weapon && availableAtLevel(action, player) && (!player.preferred || action.id === player.preferred));
  const outcome = (oldProps, nextProps) => { for (const old of oldProps) for (const next of nextProps) { const value = transitions[old]?.[next]; if (value) return {level:value[0], name:value[1], next:[value[1]]}; } return null; };
  const preferredOptions = player => actionsFor({...player, preferred:""}).sort((a,b) => b.skill_level-a.skill_level || a.name.localeCompare(b.name));
  const renderPlayers = () => {
    party.innerHTML = players.map((player,index) => {
      const weapons = [...new Set(catalog.actions.filter(action => action.jobs.includes(player.job) && (action.weapon !== "Blue Magic" || player.job === "BLU")).map(action => action.weapon))].sort((a,b) => a.localeCompare(b));
      const options = preferredOptions(player);
      return `<article class="skillchain-player"><h2>Action ${index+1}</h2><label>Job<select data-field="job" data-player="${index}"><option value="">Choose job</option>${[...catalog.jobs].sort((a,b) => a.localeCompare(b)).map(job => `<option value="${job}" ${job===player.job?"selected":""}>${job}</option>`).join("")}</select></label><label>Level<input type="number" min="1" max="75" inputmode="numeric" data-field="level" data-player="${index}" value="${player.level}" aria-label="Action ${index+1} level"></label><label>Weapon<select data-field="weapon" data-player="${index}" ${player.job?"":"disabled"}><option value="">Choose weapon</option>${weapons.map(weapon => `<option value="${escape(weapon)}" ${weapon===player.weapon?"selected":""}>${escape(weapon)}</option>`).join("")}</select></label>${player.job === "BLU" && player.weapon === "Blue Magic" ? '<p class="chain-affinity">Chain Affinity assumed active</p>' : ""}<label>Preferred action<select data-field="preferred" data-player="${index}" ${player.weapon?"":"disabled"}><option value="">Any compatible action</option>${options.map(action => `<option value="${action.id}" ${action.id===player.preferred?"selected":""}>${escape(action.name)} · ${action.level_requirement ? `Lv. ${action.level_requirement}` : `Skill ${action.skill_level}`}</option>`).join("")}</select></label></article>`;
    }).join("");
    const bluSlot = players.findIndex(player => player.job === "BLU" && player.weapon === "Blue Magic");
    const weaponFirstControl = requireWeaponSkillFirst.closest(".require-weaponskill");
    if (bluSlot >= 0 && weaponFirstControl) {
      const preferred = party.children[bluSlot].querySelector('[data-field="preferred"]').closest("label");
      weaponFirstControl.hidden = false;
      preferred.after(weaponFirstControl);
    }
    party.querySelectorAll("select,input").forEach(input => { input.addEventListener("change", event => { const index=Number(event.target.dataset.player), field=event.target.dataset.field, value=event.target.value; players[index][field] = field === "level" ? Math.min(75, Math.max(1, Number(value) || 1)) : value; if (field === "job") players[index] = {job:value,weapon:"",preferred:"",level:players[index].level}; if (field === "weapon") players[index].preferred=""; renderPlayers(); calculate(); }); if (input.dataset.field === "level") input.addEventListener("input", event => { players[Number(event.target.dataset.player)].level=Number(event.target.value); calculate(); }); });
  };
  const calculateLength = length => {
    const selected = players.map((player, slot) => ({player,slot})).filter(({player}) => actionsFor(player).length);
    if (selected.length < length) return [];
    const orders = [], buildOrders = (order, remaining) => { if (order.length === length) { orders.push(order); return; } remaining.forEach((entry,index) => buildOrders([...order,entry], [...remaining.slice(0,index),...remaining.slice(index+1)])); };
    buildOrders([], selected);
    const requiresBlueMagicOpener = requireWeaponSkillFirst.checked && selected.some(
      ({player}) => player.job === "BLU" && player.weapon === "Blue Magic"
    );
    const permittedOrders = requiresBlueMagicOpener
      ? orders.filter(order => order[0].player.weapon !== "Blue Magic" && order.slice(1).some(entry => entry.player.weapon === "Blue Magic"))
      : orders;
    const results=[];
    permittedOrders.forEach(order => { const groups=order.map(({player}) => actionsFor(player)); const walk=(index,active,steps,total)=> { if(index===length){results.push({steps,total,final:steps.at(-1).result});return;} for(const action of groups[index]) { if(!index) walk(1,action.properties,[{action,slot:order[index].slot}],action.skill_level); else { const result=outcome(active,action.properties); if(result) walk(index+1,result.next,[...steps,{action,slot:order[index].slot,result}],total+action.skill_level); } } }; walk(0,[],[],0); });
    return results;
  };
  const renderChain = chain => { const tone=chain.final.name.toLowerCase().replace(/[^a-z]+/g,"-"), elements=burstElements[chain.final.name]; return `<article class="skillchain-chain">${chain.steps.map((step,index)=>`<div class="skillchain-step"><small>Action ${step.slot+1} · ${escape(step.action.kind)}</small><strong>${escape(step.action.name)}</strong><span>${escape(step.action.properties.join(" / "))}${step.result?` → Lv.${step.result.level} ${escape(step.result.name)}`:""}</span><footer class="skillchain-jobs"><b>Jobs</b> ${escape([...step.action.jobs].sort((a,b) => a.localeCompare(b)).join(" · "))}${step.action.avatar ? ` <b>Avatar</b> ${escape(step.action.avatar)}` : ""}</footer></div>`).join("")}<div class="skillchain-result sc-${tone}">${elements.length > 1 ? `<div class="skillchain-result-elements" aria-hidden="true">${elements.map(element => `<i class="element-${element.toLowerCase()}"></i>`).join("")}</div>` : ""}<b>Lv.${chain.final.level} ${escape(chain.final.name)}</b></div></article>`; };
  const calculate = () => { const lengths=[...document.querySelectorAll(".chain-lengths input:checked")].map(input=>Number(input.value)); const results=lengths.flatMap(calculateLength).filter(chain=>!typeFilter.value || chain.final.name === typeFilter.value).sort((a,b)=>b.final.level-a.final.level || b.total-a.total || a.steps.map(step=>step.action.name).join().localeCompare(b.steps.map(step=>step.action.name).join())).slice(0,250); count.textContent=`${results.length}${results.length===250?"+":""} chains`; if (!results.length) { output.innerHTML='<p class="skillchain-empty">No valid chains for the selected action slots and filters.</p>'; syncGroupButton(); return; } const groups=new Map(); results.forEach(chain => { const group=groups.get(chain.final.name) || []; group.push(chain); groups.set(chain.final.name,group); }); output.innerHTML=[...groups.entries()].map(([name,chains]) => `<details class="skillchain-group" open><summary><span><b>Lv.${chains[0].final.level} ${escape(name)}</b><small>${chains.length} chain${chains.length===1?"":"s"}</small></span><i aria-hidden="true">⌄</i></summary><div class="skillchain-group-list">${chains.map(renderChain).join("")}</div></details>`).join(""); syncGroupButton(); };
  document.querySelectorAll(".chain-lengths input").forEach(input=>input.addEventListener("change",calculate));
  requireWeaponSkillFirst.addEventListener("change",calculate);
  typeFilter.addEventListener("change",calculate);
  [...typeFilter.options].slice(1).sort((a,b) => a.text.localeCompare(b.text)).forEach(option => typeFilter.append(option));
  Object.assign(typeFilter.parentElement.style, {display:"flex", alignItems:"center", gap:"6px", color:"#a9bed1", fontSize:"10px", fontWeight:"900", textTransform:"uppercase", letterSpacing:".06em"});
  Object.assign(typeFilter.style, {padding:"8px", border:"1px solid #365773", borderRadius:"7px", background:"#071522", color:"#f7fbff", font:"inherit", textTransform:"none", letterSpacing:"0"});
  fetch("/static/skillchain_catalog.json?v=2").then(response => response.json()).then(data => {catalog=data; summary.textContent=`${data.actions.length} Horizon-era actions loaded. Results are ordered by final skillchain level, then weapon-skill requirement.`; renderPlayers(); calculate();}).catch(() => {summary.textContent="The skillchain catalog could not be loaded.";});
})();
