(() => {
  const pad = value => String(value).padStart(2, "0");
  const today = () => {
    const date = new Date();
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  };
  const defaultTime = () => {
    const date = new Date();
    const total = Math.min(1425, Math.ceil((date.getHours() * 60 + date.getMinutes()) / 15) * 15);
    return `${pad(Math.floor(total / 60))}:${pad(total % 60)}`;
  };
  const timeOptions = () => Array.from({length: 96}, (_, index) => {
    const total = index * 15;
    const hour = Math.floor(total / 60);
    const minute = total % 60;
    const displayHour = hour % 12 || 12;
    const suffix = hour < 12 ? "AM" : "PM";
    return `<button type="button" role="option" data-time="${pad(hour)}:${pad(minute)}">${displayHour}:${pad(minute)} ${suffix}</button>`;
  }).join("");

  window.openQuarterHourPicker = (input, onChange) => {
    const current = input.value ? input.value.split("T") : [today(), defaultTime()];
    const dialog = document.createElement("dialog");
    dialog.className = "quarter-hour-dialog";
    dialog.innerHTML = `<form method="dialog"><header><div><small>Event schedule</small><h2>Choose date and time</h2></div><button value="cancel" aria-label="Close">&times;</button></header><label>Date<span class="quarter-date-control"><input type="date" name="date" required value="${current[0]}"><button type="button" class="quarter-date-button" aria-label="Open calendar" title="Open calendar"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2v3M17 2v3M3.5 9h17M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button></span></label><label>Time<span class="quarter-time-control"><input type="hidden" name="time"><button type="button" class="quarter-time-button" aria-haspopup="listbox" aria-expanded="false"></button><span class="quarter-time-menu" role="listbox" hidden>${timeOptions()}</span></span></label><footer><button class="button" value="cancel">Cancel</button><button class="button primary" value="apply">Use This Time</button></footer></form>`;
    document.body.append(dialog);
    const dateInput = dialog.querySelector('[name="date"]');
    const timeInput = dialog.querySelector('[name="time"]');
    const timeButton = dialog.querySelector('.quarter-time-button');
    const timeMenu = dialog.querySelector('.quarter-time-menu');
    const selectedTime = current[1]?.slice(0, 5) || defaultTime();
    const selectTime = value => {
      timeInput.value = value;
      const option = timeMenu.querySelector(`[data-time="${value}"]`);
      timeButton.textContent = option?.textContent || value;
      timeMenu.querySelectorAll('[data-time]').forEach(item => item.setAttribute('aria-selected', String(item === option)));
    };
    selectTime(selectedTime);
    timeButton.addEventListener('click', () => {
      const open = timeButton.getAttribute('aria-expanded') === 'true';
      timeButton.setAttribute('aria-expanded', String(!open));
      timeMenu.hidden = open;
      if (!open) timeMenu.querySelector('[aria-selected="true"]')?.scrollIntoView({block: 'center'});
    });
    timeMenu.addEventListener('click', event => {
      const option = event.target.closest('[data-time]');
      if (!option) return;
      selectTime(option.dataset.time);
      timeButton.setAttribute('aria-expanded', 'false');
      timeMenu.hidden = true;
      timeButton.focus();
    });
    dialog.querySelector(".quarter-date-button").addEventListener("click", () => {
      if (dateInput.showPicker) dateInput.showPicker();
      else dateInput.focus();
    });
    dialog.addEventListener("close", () => {
      if (dialog.returnValue === "apply") {
        const date = dialog.querySelector('[name="date"]').value;
        const time = dialog.querySelector('[name="time"]').value;
        if (date && time) {
          input.value = `${date}T${time}`;
          input.dispatchEvent(new Event("change", {bubbles: true}));
          onChange?.(input.value);
        }
      }
      dialog.remove();
    });
    dialog.showModal();
  };
})();
