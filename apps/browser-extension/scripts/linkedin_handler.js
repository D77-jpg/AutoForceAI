// linkedin_handler.js — assistive fill, no auto-submit
console.log("[Digital Employee] LinkedIn assistant loaded");

chrome.runtime.onMessage.addListener((request) => {
    if (request.action === "EXECUTE_PUBLISH") {
        performPublish(request.data || {});
    }
});

function fill(el, text) {
    if (!el) return false;
    el.focus();
    document.execCommand("selectAll");
    document.execCommand("delete");
    document.execCommand("insertText", false, text);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
}

async function performPublish(data) {
    const title = data.title || "";
    const content = data.content || "";
    const body = title && !content.startsWith(title) ? `${title}\n\n${content}` : content;

    const start = Array.from(document.querySelectorAll("button, span, div"))
        .find((n) => (n.textContent || "").trim() === "Start a post");
    if (start) start.click();
    await new Promise((r) => setTimeout(r, 1200));

    const editor =
        document.querySelector(".ql-editor") ||
        document.querySelector("div[role='textbox']") ||
        document.querySelector("[contenteditable='true']");
    if (!fill(editor, body.slice(0, 2900))) {
        alert("未找到 LinkedIn 编辑器，请先打开 Start a post 后再试。");
        return;
    }
    alert("已填入草稿。请人工检查后点击 Post（插件不会自动发布）。");
}
