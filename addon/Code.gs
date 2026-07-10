function onOpen() {
  DocumentApp.getUi()
    .createAddonMenu()
    .addItem('PageDoctor öffnen', 'showSidebar')
    .addToUi();
}

function onInstall(e) {
  onOpen();
}

function showSidebar() {
  const html = HtmlService.createHtmlOutputFromFile('Sidebar').setTitle('PageDoctor');
  DocumentApp.getUi().showSidebar(html);
}

function config_() {
  const props = PropertiesService.getScriptProperties();
  const baseUrl = props.getProperty('BACKEND_URL');
  if (!baseUrl) {
    throw new Error('BACKEND_URL ist nicht konfiguriert (Projekteinstellungen → Skripteigenschaften).');
  }
  return { baseUrl: baseUrl.replace(/\/+$/, ''), token: props.getProperty('ADDON_TOKEN') };
}

function api_(method, path, payload) {
  const cfg = config_();
  const headers = { 'ngrok-skip-browser-warning': 'true' };
  if (cfg.token) {
    headers.Authorization = 'Bearer ' + cfg.token;
  }
  const options = { method: method, muteHttpExceptions: true, headers: headers };
  if (payload !== undefined) {
    options.contentType = 'application/json';
    options.payload = JSON.stringify(payload);
  }
  const response = UrlFetchApp.fetch(cfg.baseUrl + path, options);
  const status = response.getResponseCode();
  if (status === 401) {
    throw new Error('Nicht autorisiert – prüfe den ADDON_TOKEN.');
  }
  if (status === 404) {
    throw new Error('Dieses Dokument wurde noch nicht geprüft oder ist für Sophie nicht freigegeben.');
  }
  if (status >= 300) {
    throw new Error('Backend-Fehler (' + status + ').');
  }
  const text = response.getContentText();
  return text ? JSON.parse(text) : null;
}

function docId_() {
  return encodeURIComponent(DocumentApp.getActiveDocument().getId());
}

function getFindings() {
  return api_('get', '/docs/' + docId_() + '/findings');
}

function startReview(reviewConfig) {
  return api_('post', '/docs/' + docId_() + '/review', reviewConfig);
}

function reviewStatus(runId) {
  return api_('get', '/docs/' + docId_() + '/runs/' + encodeURIComponent(runId) + '/status');
}

function getState() {
  return api_('get', '/docs/' + docId_() + '/state');
}

function resolveFinding(commentId, outcome) {
  api_(
    'post',
    '/docs/' + docId_() + '/findings/' + encodeURIComponent(commentId) + '/resolve?outcome=' + outcome
  );
  return true;
}

function jumpToQuote(quote) {
  const doc = DocumentApp.getActiveDocument();
  const found = doc.getBody().findText(quote);
  if (!found) {
    return false;
  }
  const range = doc
    .newRange()
    .addElement(found.getElement().asText(), found.getStartOffset(), found.getEndOffsetInclusive())
    .build();
  doc.setSelection(range);
  return true;
}

function applyFix(quote, replacement, commentId) {
  const found = DocumentApp.getActiveDocument().getBody().findText(quote);
  if (!found) {
    return false;
  }
  const text = found.getElement().asText();
  const start = found.getStartOffset();
  const end = found.getEndOffsetInclusive();
  text.deleteText(start, end);
  text.insertText(start, replacement);
  resolveFinding(commentId, 'applied');
  return true;
}

function dismissFinding(commentId) {
  return resolveFinding(commentId, 'dismissed');
}
