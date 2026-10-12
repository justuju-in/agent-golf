// Copy buttons on the key page. This is the only JavaScript on the site.
// Their rows start hidden: without JavaScript, or where the Clipboard API is missing
// (plain HTTP other than localhost), there are no dead buttons and the key and the
// command are still plain text that can be selected and copied.
"use strict";

if (navigator.clipboard) {
  for (const button of document.querySelectorAll("button[data-copy]")) {
    const row = button.parentElement;
    const status = row.querySelector("[role=status]");
    const text = document.getElementById(button.dataset.copy).textContent;
    let timer;
    row.hidden = false;
    button.addEventListener("click", async () => {
      clearTimeout(timer);
      try {
        await navigator.clipboard.writeText(text);
        status.textContent = "Copied";
      } catch {
        status.textContent = "Could not copy. Select the text and copy it.";
      }
      // Clear it, so copying again is announced again.
      timer = setTimeout(() => {
        status.textContent = "";
      }, 5000);
    });
  }
}
