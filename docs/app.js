// Apply branding colors from config
function applyBranding() {
  const root = document.documentElement;
  root.style.setProperty('--primary-color', BRANDING.colors.primary);
  root.style.setProperty('--secondary-color', BRANDING.colors.secondary);
  root.style.setProperty('--accent-color', BRANDING.colors.accent);
  root.style.setProperty('--background-color', BRANDING.colors.background);
  root.style.setProperty('--surface-color', BRANDING.colors.surface);
  root.style.setProperty('--text-color', BRANDING.colors.text);
  root.style.setProperty('--text-light-color', BRANDING.colors.textLight);
  root.style.setProperty('--border-color', BRANDING.colors.border);
  root.style.setProperty('--success-color', BRANDING.colors.success);
  root.style.setProperty('--error-color', BRANDING.colors.error);

  document.title = BRANDING.appName;
  document.getElementById('app-name').textContent = BRANDING.appName;
  document.getElementById('tagline').textContent = BRANDING.tagline;
  document.getElementById('footer-text').textContent = BRANDING.footer;

  if (BRANDING.logo) {
    document.getElementById('logo').src = BRANDING.logo;
    document.getElementById('logo').style.display = 'block';
  }

  if (BRANDING.favicon) {
    const link = document.createElement('link');
    link.rel = 'icon';
    link.href = BRANDING.favicon;
    document.head.appendChild(link);
  }
}

// Check API health
async function checkHealth() {
  const indicator = document.getElementById('status-indicator');
  try {
    const response = await fetch(`${BRANDING.apiEndpoint}/health`);
    if (response.ok) {
      indicator.textContent = 'Online';
      indicator.className = 'status-indicator online';
    } else {
      indicator.textContent = 'Offline';
      indicator.className = 'status-indicator offline';
    }
  } catch (error) {
    indicator.textContent = 'Offline';
    indicator.className = 'status-indicator offline';
  }
}

// Utility functions
function showResult(elementId, message, isError = false) {
  const resultDiv = document.getElementById(elementId);
  resultDiv.className = `result show ${isError ? 'error' : 'success'}`;
  resultDiv.innerHTML = message;
}

function setButtonLoading(button, isLoading) {
  if (isLoading) {
    button.disabled = true;
    button.innerHTML += '<span class="spinner"></span>';
  } else {
    button.disabled = false;
    const spinner = button.querySelector('.spinner');
    if (spinner) spinner.remove();
  }
}

// Count endpoint
async function handleCount() {
  const fileInput = document.getElementById('count-file');
  const button = document.getElementById('count-btn');
  const resultDiv = document.getElementById('count-result');

  if (!fileInput.files[0]) {
    showResult('count-result', 'Please select a file', true);
    return;
  }

  setButtonLoading(button, true);

  try {
    const formData = new FormData();
    formData.append('input_file', fileInput.files[0]);

    const response = await fetch(`${BRANDING.apiEndpoint}/count`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let result = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(line => line.trim());

      for (const line of lines) {
        try {
          const json = JSON.parse(line);
          result += `<div>${JSON.stringify(json, null, 2)}</div>`;
        } catch (e) {
          result += `<div>${line}</div>`;
        }
      }
    }

    showResult('count-result', `<pre>${result}</pre>`);
  } catch (error) {
    showResult('count-result', `Error: ${error.message}`, true);
  } finally {
    setButtonLoading(button, false);
  }
}

// Convert endpoint
async function handleConvert() {
  const fileInput = document.getElementById('convert-file');
  const formatSelect = document.getElementById('convert-format');
  const button = document.getElementById('convert-btn');

  if (!fileInput.files[0]) {
    showResult('convert-result', 'Please select a file', true);
    return;
  }

  setButtonLoading(button, true);

  try {
    const formData = new FormData();
    formData.append('input_file', fileInput.files[0]);
    formData.append('to', formatSelect.value);

    const response = await fetch(`${BRANDING.apiEndpoint}/convert`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `converted.${formatSelect.value === 'marcxml' ? 'xml' : formatSelect.value}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showResult('convert-result', 'File converted and downloaded successfully');
  } catch (error) {
    showResult('convert-result', `Error: ${error.message}`, true);
  } finally {
    setButtonLoading(button, false);
  }
}

// Split endpoint
async function handleSplit() {
  const fileInput = document.getElementById('split-file');
  const everyInput = document.getElementById('split-every');
  const formatSelect = document.getElementById('split-format');
  const button = document.getElementById('split-btn');

  if (!fileInput.files[0]) {
    showResult('split-result', 'Please select a file', true);
    return;
  }

  if (!everyInput.value || everyInput.value <= 0) {
    showResult('split-result', 'Please enter a valid number of records', true);
    return;
  }

  setButtonLoading(button, true);

  try {
    const formData = new FormData();
    formData.append('input_file', fileInput.files[0]);
    formData.append('every', everyInput.value);
    if (formatSelect.value) {
      formData.append('to', formatSelect.value);
    }

    const response = await fetch(`${BRANDING.apiEndpoint}/split`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'split_output.zip';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showResult('split-result', 'Files split and downloaded as ZIP successfully');
  } catch (error) {
    showResult('split-result', `Error: ${error.message}`, true);
  } finally {
    setButtonLoading(button, false);
  }
}

// Merge endpoint
async function handleMerge() {
  const fileInput = document.getElementById('merge-files');
  const formatSelect = document.getElementById('merge-format');
  const button = document.getElementById('merge-btn');

  if (!fileInput.files.length) {
    showResult('merge-result', 'Please select at least one file', true);
    return;
  }

  setButtonLoading(button, true);

  try {
    const formData = new FormData();
    for (let i = 0; i < fileInput.files.length; i++) {
      formData.append('files', fileInput.files[i]);
    }
    formData.append('to', formatSelect.value);

    const response = await fetch(`${BRANDING.apiEndpoint}/merge`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `merged.${formatSelect.value === 'marcxml' ? 'xml' : formatSelect.value}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showResult('merge-result', 'Files merged and downloaded successfully');
  } catch (error) {
    showResult('merge-result', `Error: ${error.message}`, true);
  } finally {
    setButtonLoading(button, false);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  applyBranding();
  checkHealth();

  // Set up event listeners
  document.getElementById('count-btn').addEventListener('click', handleCount);
  document.getElementById('convert-btn').addEventListener('click', handleConvert);
  document.getElementById('split-btn').addEventListener('click', handleSplit);
  document.getElementById('merge-btn').addEventListener('click', handleMerge);

  // Check health every 30 seconds
  setInterval(checkHealth, 30000);
});
