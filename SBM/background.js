let activeTab = null;
let startTime = null;
let tabStartTimes = {};
let tabTitles = {};

function sendToFlaskServer(data) {
    fetch("http://localhost:5000/log_activity", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    }).then(response => response.json())
    .then(data => console.log("✅ Data saved:", data))
    .catch(error => console.error("❌ Error sending data to Flask server:", error));
}

function logExitActivity(tabId) {
    if (activeTab && startTime) {
        let exitTime = new Date();
        let duration = (exitTime - startTime) / 1000;

        let data = {
            action: "save_activity",
            url: activeTab,
            title: tabTitles[tabId] || "Unknown",
            enter_time: startTime.toISOString(),
            exit_time: exitTime.toISOString(),
            duration: duration
        };

        sendToFlaskServer(data);
        console.log(`⏳ Exited: ${activeTab} at ${exitTime.toLocaleTimeString()} (Duration: ${duration}s)`);
    }
}

async function logEntryActivity(tabId) {
    let tab = await chrome.tabs.get(tabId);
    if (tab.url) {
        activeTab = tab.url;
        startTime = new Date();
        tabStartTimes[tabId] = startTime;
        tabTitles[tabId] = tab.title || "Unknown";

        console.log(`🌐 Entered: ${activeTab}`);
        console.log(`📌 Title: ${tabTitles[tabId]}`);
        console.log(`🕒 Time: ${startTime.toLocaleTimeString()}`);
    }
}

chrome.tabs.onActivated.addListener(async (activeInfo) => {
    let previousTabId = Object.keys(tabStartTimes).find(id => id !== activeInfo.tabId.toString());
    if (previousTabId) logExitActivity(parseInt(previousTabId));
    logEntryActivity(activeInfo.tabId);
});

chrome.webNavigation.onCommitted.addListener((details) => {
    if (details.frameId === 0) {
        logExitActivity(details.tabId);
        logEntryActivity(details.tabId);
    }
});

chrome.tabs.onRemoved.addListener((tabId) => {
    logExitActivity(tabId);
    delete tabStartTimes[tabId];
    delete tabTitles[tabId];
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.title) {
        tabTitles[tabId] = changeInfo.title;
    }
});

console.log("🚀 Background script started!");
