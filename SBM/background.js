let activeTab = null;
let startTime = null;
let tabStartTimes = {};
let tabTitles = {};

function sendToFlaskServer(data) {
    fetch("http://localhost:5000/log_activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return response.json();  // Parse JSON only if response is OK
    })
    .then(data => console.log("✅ Data sent:", data))
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
    try {
        let tab = await chrome.tabs.get(activeInfo.tabId);

        if (!tab.url || !tab.url.startsWith("http")) {
            console.warn("⚠️ Ignoring non-webpage URL:", tab.url || "No URL found");
            return; // Skip non-http URLs
        }

        let urlSafety = await checkUrlSafety(tab.url);
        console.log('The URL safety is:', urlSafety.safe);

        let siteData = {
            url: tab.url,
            title: tab.title || "Unknown Page",
            safe: urlSafety.safe,
            message: urlSafety.message
        };

        // Store visited sites in Chrome storage (limit to last 10 entries)
        chrome.storage.local.get(["visitedSites"], (result) => {
            let visitedSites = result.visitedSites || [];
            visitedSites.unshift(siteData); // Add new entry at the top
            if (visitedSites.length > 10) visitedSites.pop(); // Keep last 10 entries
            chrome.storage.local.set({ visitedSites });
        });

        if (!urlSafety.safe) {
            showUnsafePopup(urlSafety.message);
            console.warn(`🚨 Unsafe URL detected: ${tab.url} - ${urlSafety.message}`);
            return; // Stop further processing if the site is unsafe
        }

        let data = {
            action: "log_tab_switch",
            url: tab.url,
            domain: new URL(tab.url).hostname,
            tab_id: tab.id,
            window_id: tab.windowId,
            timestamp: new Date().toISOString()
        };

        sendToFlaskServer(data);
        console.log(`🔄 Switched to safe tab: ${tab.url}`);
    } catch (error) {
        console.error("❌ Error processing tab switch:", error);
    }
});


// Function to check URL safety using Google Safe Browsing API
async function checkUrlSafety(url) {
    const apiKey = "AIzaSyBQwJUKKgsZSSvUvvfwICx4tJ4THRLMULA";
    const endpoint = `https://safebrowsing.googleapis.com/v4/threatMatches:find?key=${apiKey}`;

    const requestPayload = {
        client: {
            clientId: "your-client-id",
            clientVersion: "1.0"
        },
        threatInfo: {
            threatTypes: ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            platformTypes: ["WINDOWS", "LINUX", "ALL_PLATFORMS"],
            threatEntryTypes: ["URL"],
            threatEntries: [
                { url: url }
            ]
        }
    };

    try {
        console.log("🔍 Checking URL safety:", url);
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(requestPayload)
        });

        if (!response.ok) {
            console.error("❌ Failed to connect to Google Safe Browsing API:", response.status);
            return { safe: true }; // Assume safe if API call fails
        }

        const result = await response.json();
        if (result && result.matches && result.matches.length > 0) {
            return {
                safe: false,
                message: `This URL is flagged as ${result.matches[0].threatType}`
            };
        }

        return { safe: true }; // URL is safe
    } catch (error) {
        console.error("❌ Error during URL safety check:", error);
        return { safe: true }; // Assume safe if API call fails
    }
}

// Function to show a popup for unsafe URLs
function showUnsafePopup(message) {
    chrome.notifications.create({
        type: "basic",
        iconUrl: "icon.png", // Path to your extension's icon
        title: "Unsafe Website Detected",
        message: message,
        priority: 2
    });
}



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