(() => {
  'use strict';
  const form = document.getElementById('sample-form');
  const status = document.getElementById('copy-status');
  const fallback = document.getElementById('prepared-request');
  const email = document.getElementById('email-request');
  if (!form) return;
  form.addEventListener('input', () => {
    email.hidden = true;
    fallback.hidden = true;
    fallback.value = '';
    status.textContent = '';
  });
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
    email.href = `mailto:raphael.caillon.engineer@gmail.com?subject=Scoop%20sample%20request&body=${encodeURIComponent(message)}`;
    email.hidden = false;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(message);
      fallback.hidden = true;
      status.textContent = 'Copied. Paste it into your email, or open a draft below.';
    } catch {
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
      status.textContent = 'Your request is ready below. Copy it or open an email draft.';
    }
  });
})();
