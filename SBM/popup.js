document.addEventListener("DOMContentLoaded", async () => {
    const urlList = document.getElementById("urlList");
    
    chrome.storage.local.get(["visitedSites"], (result) => {
        const visitedSites = result.visitedSites || [];

        if (visitedSites.length === 0) {
            urlList.innerHTML = `<p class="text-gray-500 text-center">No browsing data available.</p>`;
            return;
        }

        urlList.innerHTML = ""; // Clear previous entries

        visitedSites.forEach(({ url, title, safe, message }) => {
            const item = document.createElement("div");
            item.className = "p-2 rounded bg-gray-800 flex justify-between items-center";

            item.innerHTML = `
                <div class="flex-1">
                    <p class="text-sm truncate">${title || "Unknown Page"}</p>
                    <a href="${url}" target="_blank" class="text-blue-400 text-xs truncate">${url}</a>
                </div>
                <span class="text-xs font-semibold px-2 py-1 rounded ${
                    safe ? "bg-green-500 text-white" : "bg-red-500 text-white"
                }">
                    ${safe ? "Safe" : "Unsafe"}
                </span>
            `;

            urlList.appendChild(item);
        });
    });
});
