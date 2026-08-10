(() => {
  const modal = document.querySelector("#spell-map-modal");
  if (!modal) return;
  const dialog = modal.querySelector(".spawn-dialog");
  const stage = document.querySelector("#spell-map-stage");
  const wrap = document.querySelector("#spell-map-wrap");
  const image = document.querySelector("#spell-map-image");
  const markers = document.querySelector("#spell-map-markers");
  const pages = document.querySelector("#spell-map-pages");
  const empty = document.querySelector("#spell-map-empty");
  let requestVersion = 0;

  const monsterNames = text => {
    const parts = text.split(",").map(name => name.trim()).filter(Boolean);
    if (parts.length < 2) return parts;
    const prefix = parts[0].split(/\s+/)[0];
    return parts.map((name, index) => index && !name.includes(" ") ? `${prefix} ${name}` : name);
  };
  const close = () => {
    modal.hidden = true;
    document.body.classList.remove("map-modal-open");
    dialog.style.cssText = "";
  };
  const markerNode = marker => {
    const pin = document.createElement("i");
    pin.className = "spell-map-pin";
    pin.style.left = `${marker.left}%`;
    pin.style.top = `${marker.top}%`;
    pin.dataset.mob = marker.mob;
    pin.title = `${marker.mob} spawn`;
    return pin;
  };
  const showMap = (maps, combinedMarkers, map, index, zone) => {
    wrap.hidden = true;
    wrap.style.width = "";
    wrap.dataset.zoom = "1";
    stage.scrollTo(0, 0);
    image.onload = () => { empty.hidden = true; wrap.hidden = false; };
    image.src = map.url;
    image.alt = `${zone}, ${map.label || `map ${index + 1}`}`;
    markers.replaceChildren(...combinedMarkers.filter(marker => marker.map_id === map.map_id).map(markerNode));
    pages.querySelectorAll("button").forEach((button, buttonIndex) => button.classList.toggle("active", buttonIndex === index));
  };

  window.openSpellTargetMap = async (zone, monsterText) => {
    const version = ++requestVersion;
    const mobs = monsterNames(monsterText);
    document.querySelector("#spell-map-zone").textContent = zone;
    document.querySelector("#spell-map-title").textContent = monsterText;
    document.querySelector("#spell-map-count").textContent = "Loading...";
    document.querySelector("#spell-map-legend").textContent = mobs.join(" / ");
    markers.replaceChildren();
    pages.replaceChildren();
    pages.hidden = true;
    wrap.hidden = true;
    empty.hidden = true;
    modal.hidden = false;
    document.body.classList.add("map-modal-open");
    document.querySelector("#spell-map-close").focus();
    const responses = await Promise.all(mobs.map(async mob => {
      try {
        const response = await fetch(`/api/map-assets?zone=${encodeURIComponent(zone)}&mob=${encodeURIComponent(mob)}`);
        return { mob, data: response.ok ? await response.json() : { maps: [] } };
      } catch (_error) {
        return { mob, data: { maps: [] } };
      }
    }));
    if (version !== requestVersion) return;
    const source = responses.find(result => result.data.maps && result.data.maps.length);
    if (!source) {
      empty.hidden = false;
      document.querySelector("#spell-map-count").textContent = "No map";
      return;
    }
    const maps = source.data.maps;
    const combined = responses.flatMap(({ mob, data }) => {
      const points = data.markers || (data.marker ? [data.marker] : []);
      return points.map(point => ({ ...point, mob }));
    });
    document.querySelector("#spell-map-count").textContent = `${combined.length} spawn${combined.length === 1 ? "" : "s"}`;
    pages.replaceChildren(...maps.map((map, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = map.label || `Map ${index + 1}`;
      button.addEventListener("click", () => showMap(maps, combined, map, index, zone));
      return button;
    }));
    pages.hidden = maps.length < 2;
    const preferred = responses.flatMap(result => result.data.markers || []).find(Boolean)?.map_id || source.data.preferred_map;
    const selected = Math.max(0, maps.findIndex(map => map.map_id === preferred));
    showMap(maps, combined, maps[selected], selected, zone);
  };

  document.querySelector("#spell-map-close").addEventListener("click", close);
  modal.addEventListener("click", event => { if (event.target === modal) close(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !modal.hidden) close(); });
  stage.addEventListener("wheel", event => {
    if (wrap.hidden) return;
    event.preventDefault();
    const current = Number(wrap.dataset.zoom || 1);
    const next = Math.max(1, Math.min(3, current + (event.deltaY < 0 ? .2 : -.2)));
    if (next === current) return;
    const base = wrap.offsetWidth / current;
    wrap.dataset.zoom = String(next);
    wrap.style.width = `${base * next}px`;
  }, { passive: false });
  let pan = null;
  stage.addEventListener("pointerdown", event => {
    if (Number(wrap.dataset.zoom || 1) <= 1 || event.button !== 0) return;
    pan = { x: event.clientX, y: event.clientY, left: stage.scrollLeft, top: stage.scrollTop };
    stage.classList.add("is-panning");
    stage.setPointerCapture(event.pointerId);
  });
  stage.addEventListener("pointermove", event => {
    if (!pan) return;
    stage.scrollLeft = pan.left - (event.clientX - pan.x);
    stage.scrollTop = pan.top - (event.clientY - pan.y);
  });
  const stopPan = () => { pan = null; stage.classList.remove("is-panning"); };
  stage.addEventListener("pointerup", stopPan);
  stage.addEventListener("pointercancel", stopPan);
})();
