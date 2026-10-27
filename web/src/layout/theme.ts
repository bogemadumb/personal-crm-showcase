export function toggleTheme() {
  const dark = document.documentElement.dataset.theme !== 'dark'
  if (dark) document.documentElement.dataset.theme = 'dark'
  else delete document.documentElement.dataset.theme
  try { localStorage.setItem('crm.theme', dark ? 'dark' : 'light') } catch { /* приватный режим */ }
}
