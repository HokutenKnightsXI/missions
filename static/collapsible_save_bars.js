document.querySelectorAll('.collapsible-save-bar').forEach(bar=>{
  const toggle=bar.querySelector('.save-bar-toggle');
  if(!toggle)return;
  toggle.addEventListener('click',()=>{
    const collapsed=bar.classList.toggle('is-collapsed');
    toggle.setAttribute('aria-expanded',String(!collapsed));
    toggle.setAttribute('aria-label',collapsed?'Expand save bar':'Collapse save bar');
  });
});
