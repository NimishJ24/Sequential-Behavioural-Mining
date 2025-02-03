document.getElementById("clear").addEventListener("click", () => {
    console.clear();
    alert("Console Cleared!");
});

document.getElementById("printStats").addEventListener("click", async () => {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) {
            console.log(`Current Tab URL: ${tab.url}`);
            console.log(`Current Tab Title: ${tab.title}`);
            alert(`Details printed in console:\nURL: ${tab.url}\nTitle: ${tab.title}`);
        } else {
            alert("No active tab found.");
        }
    } catch (error) {
        console.error("Error retrieving tab details:", error);
        alert("Error occurred. Check the console.");
    }
});
