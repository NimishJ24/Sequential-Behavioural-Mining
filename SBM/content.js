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

document.addEventListener('click', (event) => {
    let data = {
        action: "mouse_click",
        timestamp: new Date().toISOString(),
        x: event.clientX,
        y: event.clientY,
        element: event.target.tagName,
        url: window.location.href
    };
    sendToFlaskServer(data);
    console.log(`🖱️ Mouse click at (${event.clientX}, ${event.clientY}) on ${event.target.tagName}`);
});



document.addEventListener('keydown', (event) => {
    let data = {
        action: "key_press",
        timestamp: new Date().toISOString(),
        key: event.key,
        url: window.location.href
    };
    sendToFlaskServer(data);
    console.log(`⌨️ Key pressed: ${event.key}`);
});
