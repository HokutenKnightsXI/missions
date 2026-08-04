const mode = document.querySelector('#availability-mode');
const cap = document.querySelector('[name="level_cap"]');
const activity = document.querySelector('#help-activity');
const zoneValue = document.querySelector('#zone-value');
const zoneSelect = document.querySelector('#zone-select');
const zoneText = document.querySelector('#zone-text');
const helpZones = JSON.parse(document.querySelector('#help-zones-data')?.textContent || '{}');
function syncZoneField() {
  if (!activity || !zoneValue) return;
  const groups = helpZones[activity.value];
  if (groups) {
    const previous = zoneValue.value;
    zoneSelect.replaceChildren(new Option('Choose a region / zone…', ''));
    const choices = [];
    Object.entries(groups).forEach(([region, zones]) => {
      const group = document.createElement('optgroup'); group.label = region;
      zones.forEach(zone => { group.appendChild(new Option(zone, zone)); choices.push(zone); });
      zoneSelect.appendChild(group);
    });
    zoneSelect.hidden = false; zoneText.hidden = true; zoneSelect.value = choices.includes(previous) ? previous : '';
    zoneValue.value = zoneSelect.value;
  } else {
    zoneSelect.hidden = true; zoneText.hidden = false; zoneText.value = zoneValue.value;
  }
}
function syncRequestForm() {
  if (mode) {
    document.querySelector('[data-time-field="start"]').hidden = mode.value !== 'fixed';
    document.querySelector('[data-time-field="after"]').hidden = mode.value !== 'after';
  }
  const minimum = Number(cap?.value || 0);
  document.querySelectorAll('[data-job-level]').forEach(label => {
    const eligible = !minimum || Number(label.dataset.jobLevel) >= minimum;
    label.classList.toggle('eligible', eligible); label.classList.toggle('ineligible', !eligible);
    const input = label.querySelector('input'); input.disabled = !eligible; if (!eligible) input.checked = false;
  });
}
mode?.addEventListener('change', syncRequestForm); cap?.addEventListener('input', syncRequestForm); syncRequestForm();
activity?.addEventListener('change', syncZoneField); zoneSelect?.addEventListener('change', () => { zoneValue.value = zoneSelect.value; }); zoneText?.addEventListener('input', () => { zoneValue.value = zoneText.value; }); syncZoneField();
document.querySelector('#select-any-jobs')?.addEventListener('click', () => {
  document.querySelectorAll('[name="requested_jobs"]').forEach(input => { input.checked = true; });
  document.querySelectorAll('[name^="requested_count_job_"]').forEach(select => { select.value = ''; });
});
