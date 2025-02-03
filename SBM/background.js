let activeTab = null;
let startTime = null;
let tabStartTimes = {};

// Send data to Native Messaging Host (Python script)
function sendToNativeHost(data) {
    chrome.runtime.sendNativeMessage("com.sbm.native_host", data, (response) => {
        if (chrome.runtime.lastError) {
            console.error("Native Host Error:", chrome.runtime.lastError.message);
        } else {
            console.log("✅ Data saved:", response);
        }
    });
}

// Function to log exit activity
function logExitActivity(tabId) {
    if (activeTab && startTime) {
        let exitTime = new Date();
        let duration = (exitTime - startTime) / 1000; // Convert to seconds

        let data = {
            action: "save_activity",
            url: activeTab,
            title: "Unknown", // Title will be updated in logEntryActivity
            enter_time: startTime.toISOString(),
            exit_time: exitTime.toISOString(),
            duration: duration
        };

        sendToNativeHost(data);

        console.log(`⏳ Exited: ${activeTab} at ${exitTime.toLocaleTimeString()} (Duration: ${duration}s)`);
    }
}

// Function to log entry activity
async function logEntryActivity(tabId) {
    let tab = await chrome.tabs.get(tabId);
    if (tab.url) {
        activeTab = tab.url;
        startTime = new Date();
        tabStartTimes[tabId] = startTime;

        console.log(`🌐 Entered: ${activeTab}`);
        console.log(`📌 Title: ${tab.title}`);
        console.log(`🕒 Time: ${startTime.toLocaleTimeString()}`);
    }
}

// Detect tab switches
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    let previousTabId = Object.keys(tabStartTimes).find(id => id !== activeInfo.tabId.toString());

    if (previousTabId) logExitActivity(parseInt(previousTabId));
    logEntryActivity(activeInfo.tabId);
});

// Detect navigation within the same tab
chrome.webNavigation.onCommitted.addListener((details) => {
    if (details.frameId === 0) {
        logExitActivity(details.tabId);
        logEntryActivity(details.tabId);
    }
});

// Detect when a tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
    logExitActivity(tabId);
    delete tabStartTimes[tabId];
});

console.log("🚀 Background script started!");