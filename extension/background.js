// Clicking the toolbar button opens the panel beside the page.
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(function () {});

// On any site: select text, right-click, "Unmask this text".
chrome.runtime.onInstalled.addListener(function () {
  chrome.contextMenus.create({ id: "decode-selection", title: "Unmask this text", contexts: ["selection"] });
});

chrome.contextMenus.onClicked.addListener(function (info, tab) {
  if (info.menuItemId !== "decode-selection" || !info.selectionText) return;
  // The panel may not be open yet, so the text waits in session storage for it.
  chrome.storage.session.set({ pending: { text: info.selectionText.slice(0, 5000), at: Date.now() } });
  if (tab && tab.id != null) chrome.sidePanel.open({ tabId: tab.id }).catch(function () {});
});
