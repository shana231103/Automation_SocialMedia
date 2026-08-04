# File: backend/app/infrastructure/automation/adapters/sensitive_mask.py
"""JavaScript used to mask editable fields while browser screenshots are taken."""

MASK_SENSITIVE_SCRIPT = """
() => {
  const id = '__automation_sensitive_mask__';
  if (document.getElementById(id)) return;
  const style = document.createElement('style');
  style.id = id;
  style.textContent = `
    input, textarea, [contenteditable="true"] {
      filter: blur(10px) !important;
      color: transparent !important;
      text-shadow: none !important;
      caret-color: transparent !important;
    }
    input::placeholder, textarea::placeholder { color: transparent !important; }
  `;
  document.documentElement.appendChild(style);
}
"""

REMOVE_SENSITIVE_MASK_SCRIPT = """
() => document.getElementById('__automation_sensitive_mask__')?.remove()
"""
