/* WEB-03 progressive enhancement only: no game rules in JavaScript.
 * All actions still execute through the original localhost CSRF-protected
 * PlayerGateway. Without JavaScript the same HTML forms continue to work.
 */
(() => {
  "use strict";
  let busy = false;

  // Update the displayed quote total; the server independently revalidates
  // quantity, physical stock, owned cash and original quote unit price.
  document.addEventListener("input", (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.name !== "quantity") return;
    const form = input.closest("form.buy-form");
    if (!form) return;
    const output = form.querySelector("output");
    if (!output) return;
    const qty = Number(input.value);
    const price = Number(form.dataset.unitPrice);
    if (!Number.isSafeInteger(qty) || !Number.isSafeInteger(price) ||
        qty < Number(input.min) || qty > Number(input.max)) {
      output.textContent = "اختر كمية ضمن المخزون وميزانيتك.";
      return;
    }
    output.textContent = "الإجمالي: " + (qty * price) + " نحاس";
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.getAttribute("action") !== "/act") return;
    if (!form.checkValidity()) return;
    event.preventDefault();
    if (busy) return; // Never execute a player's command twice from a double-click.
    busy = true;
    const disabled = Array.from(document.querySelectorAll("button[type=submit]"));
    for (const button of disabled) button.disabled = true;

    try {
      const body = new URLSearchParams(new FormData(form));
      const response = await fetch("/act", {
        method: "POST",
        body,
        headers: {"X-Carlos-Partial": "1"},
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok || response.headers.get("X-Carlos-Partial") !== "1") {
        throw new Error("فشل الطلب المحلي: " + response.status);
      }
      const newPage = new DOMParser().parseFromString(await response.text(), "text/html");
      const newMain = newPage.querySelector("main");
      const oldMain = document.querySelector("main");
      if (!newMain || !oldMain) throw new Error("تعذّر قراءة نتيجة الأمر.");
      const y = window.scrollY;
      oldMain.replaceWith(document.importNode(newMain, true));
      window.scrollTo(0, y);
    } catch (err) {
      const status = document.querySelector('[role="status"]');
      if (status) status.textContent = "تعذر تحديث اللعبة. " +
        (err instanceof Error ? err.message : "خطأ اتصال محلي.") +
        " تحقق من تشغيل نافذة Python.";
    } finally {
      busy = false;
      for (const button of disabled) button.disabled = false;
    }
  });
})();
