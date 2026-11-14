# Unmasked extension

1. Open `chrome://extensions`, switch on "Developer mode", press "Load unpacked" and pick this `extension/` folder.
2. Open a Bluesky post or a YouTube video and click the extension's toolbar button: a panel opens beside the page with the analysis.
3. On any other site, select text, right-click and choose "Unmask this text".

The extension holds no keys. It sends the tab's link (or the text you selected) to the server in `config.js`.
`panel.js`, `panel.css` and `app.js` are copies of the files in `web/`; a test keeps them identical.
