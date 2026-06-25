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

function getFindings() {
  const props = PropertiesService.getScriptProperties();
  const baseUrl = props.getProperty('BACKEND_URL');
  if (!baseUrl) {
    throw new Error('BACKEND_URL ist nicht konfiguriert (Projekteinstellungen → Skripteigenschaften).');
  }
  const token = props.getProperty('ADDON_TOKEN');
  const docId = DocumentApp.getActiveDocument().getId();

  const headers = { 'ngrok-skip-browser-warning': 'true' };
  if (token) {
    headers.Authorization = 'Bearer ' + token;
  }
  const options = {
    method: 'get',
    muteHttpExceptions: true,
    headers: headers,
  };
  const response = UrlFetchApp.fetch(
    baseUrl.replace(/\/+$/, '') + '/docs/' + encodeURIComponent(docId) + '/findings',
    options
  );

  const status = response.getResponseCode();
  if (status === 401) {
    throw new Error('Nicht autorisiert – prüfe den ADDON_TOKEN.');
  }
  if (status === 404) {
    throw new Error('Dieses Dokument wurde noch nicht geprüft oder ist für Sophie nicht freigegeben.');
  }
  if (status !== 200) {
    throw new Error('Backend-Fehler (' + status + ').');
  }
  return JSON.parse(response.getContentText());
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

function applyFix(quote, replacement) {
  const found = DocumentApp.getActiveDocument().getBody().findText(quote);
  if (!found) {
    return false;
  }
  const text = found.getElement().asText();
  const start = found.getStartOffset();
  const end = found.getEndOffsetInclusive();
  text.deleteText(start, end);
  text.insertText(start, replacement);
  return true;
}
