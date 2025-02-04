function sendToFlaskServer(data) {
    fetch("http://localhost:5001/log_activity", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    }).then(response => response.json())
    .then(data => console.log("✅ Data saved:", data))
    .catch(error => console.error("❌ Error sending data to Flask server:", error));
}

document.addEventListener('click', (event) => {
    let data = {
        action: "log_mouse_click",
        timestamp: new Date().toISOString(),
        x: event.clientX,
        y: event.clientY,
        element: event.target.tagName,
        url: window.location.href
    };
    sendToFlaskServer(data);
    console.log(`🖱️ Mouse click at (${event.clientX}, ${event.clientY}) on ${event.target.tagName}`);
});

document.addEventListener('click', (event) => {
    if (event.target.tagName === "A" && event.target.href) {
        let data = {
            action: "log_link_click",
            timestamp: new Date().toISOString(),
            url: event.target.href,
            referrer: document.referrer
        };
        sendToFlaskServer(data);
        console.log(`🔗 Link clicked: ${event.target.href}`);
    }
});

document.addEventListener('keydown', (event) => {
    let data = {
        action: "log_key_press",
        timestamp: new Date().toISOString(),
        key: event.key,
        url: window.location.href
    };
    sendToFlaskServer(data);
    console.log(`⌨️ Key pressed: ${event.key}`);
});
