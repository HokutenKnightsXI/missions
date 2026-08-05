(()=>{
  const tooltip=document.querySelector('#item-stat-tooltip'),tracker=document.querySelector('.loot-tracker-form');
  if(!tooltip||!tracker)return;
  let items={},active=null;
  fetch(window.ITEM_TOOLTIP_URL).then(response=>response.json()).then(data=>items=data).catch(()=>{});
  const owner=target=>target.closest('.tracked-item,.paired-piece');
  const place=(x,y)=>{const pad=12,rect=tooltip.getBoundingClientRect();tooltip.style.left=`${Math.max(pad,Math.min(innerWidth-rect.width-pad,x+16))}px`;tooltip.style.top=`${Math.max(pad,Math.min(innerHeight-rect.height-pad,y+16))}px`};
  const show=(row,x,y)=>{const key=row?.querySelector('input[name="owned"]')?.value,item=items[key];if(!item)return;active=row;document.querySelector('#tooltip-job').textContent=item.job;document.querySelector('#tooltip-name').textContent=item.name;document.querySelector('#tooltip-meta').textContent=`${item.slot}${item.level?` · Level ${item.level}`:''}`;document.querySelector('#tooltip-stats').textContent=item.note?`${item.note}\n\n${item.stats}`:item.stats;tooltip.hidden=false;place(x,y)};
  const hide=row=>{if(!row||row===active){tooltip.hidden=true;active=null}};
  tracker.addEventListener('pointerover',event=>{const row=owner(event.target);if(row&&row!==active)show(row,event.clientX,event.clientY)});
  tracker.addEventListener('pointermove',event=>{if(active)place(event.clientX,event.clientY)});
  tracker.addEventListener('pointerout',event=>{const row=owner(event.target);if(row&&!row.contains(event.relatedTarget))hide(row)});
  tracker.addEventListener('focusin',event=>{const row=owner(event.target);if(row){const rect=row.getBoundingClientRect();show(row,rect.right,rect.top)}});
  tracker.addEventListener('focusout',event=>{const row=owner(event.target);if(row&&!row.contains(event.relatedTarget))hide(row)});
})();
