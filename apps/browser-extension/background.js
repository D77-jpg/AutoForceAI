// background.js - 只有这里可以调用 chrome.tabs.create 等高级API

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_RPA_TASK") {
        handleRPATask(request.data);
        sendResponse({ status: "accepted" });
    }
});

async function handleRPATask(taskData) {
    let targetUrl = "";
    if (taskData.platform === "redbook") {
        targetUrl = "https://creator.xiaohongshu.com/publish/publish";
    } else if (taskData.platform === "douyin") {
        targetUrl = "https://creator.douyin.com/";
    } else if (taskData.platform === "linkedin") {
        targetUrl = "https://www.linkedin.com/feed/";
    }

    if (!targetUrl) return;

    // 1. 打开对应的创作平台 (在新标签页)
    const tab = await chrome.tabs.create({ url: targetUrl, active: true });

    // 2. 监听标签页加载完成，然后发送数据给 Content Script 开始干活
    chrome.tabs.onUpdated.addListener(function listener(tabId, changeInfo) {
        if (tabId === tab.id && changeInfo.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(listener); 
            
            // 安全等待一下页面初始化
            setTimeout(() => {
                chrome.tabs.sendMessage(tabId, {
                    action: "EXECUTE_PUBLISH",
                    data: taskData
                }).catch(err => console.log("Content Script not ready yet?", err));
            }, 3000);
        }
    });
}
