(() => {
  'use strict';
  const form = document.getElementById('sample-form');
  const status = document.getElementById('copy-status');
  const fallback = document.getElementById('prepared-request');
  if (!form) return;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const offer = document.getElementById('offer').value.trim();
    const accounts = document.getElementById('accounts').value.split('\n').map(value => value.trim()).filter(Boolean);
    if (!offer || accounts.length !== 3) {
      status.textContent = 'Describe your offer and add exactly three accounts, one per line.';
      return;
    }
    const message = `Hi Scoop,\n\nI would like to see a sample brief for our team.\n\nWhat we sell: ${offer}\n\nThree target accounts:\n${accounts.map((value, index) => `${index + 1}. ${value}`).join('\n')}\n\nPlease confirm the sample and paid pilot scope with me.\n`;
    fallback.value = message;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(message);
      fallback.hidden = true;
      status.textContent = 'Copied. Paste this into your reply to Scoop.';
    } catch {
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
      status.textContent = 'Your request is ready below. Copy it and paste it into your reply to Scoop.';
    }
  });
})();
