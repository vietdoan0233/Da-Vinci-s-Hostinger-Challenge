# Oxylabs Web API integration

The live-context flow uses two Oxylabs Web API endpoints at runtime:

- POST /v1/search finds public pages relevant to a checkable claim extracted from the post.
- POST /v1/scrape reads up to four distinct public pages as Markdown so the model can summarize the pages themselves rather than relying on search snippets.

The API key is read from OXYLABS_WEB_API_KEY on the server and is never sent to the browser. The result displays the source URLs, distinguishes pages that were fully read from search-only results, and links each summary item to the source IDs that support it. The model is instructed to report only perspectives present in the retrieved pages; it does not issue a true/false verdict or force equal sides.

If there is no checkable claim, no eligible result, or no readable page, the response explains that state instead of fabricating a conclusion. The displayed notes also clarify that search is a sample of the web and that ranking is not a measure of truth.
