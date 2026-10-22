// PocketDrop Frontend JavaScript — Pure Vanilla JS (No CDNs)

document.addEventListener("DOMContentLoaded", () => {
    const statusBadge = document.getElementById("connection-status");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    // Check server status
    async function checkStatus() {
        try {
            const response = await fetch("/api/status");
            if (response.ok) {
                const data = await response.json();
                statusBadge.textContent = "Online";
                statusBadge.className = "status-badge online";
            } else {
                statusBadge.textContent = "Error";
                statusBadge.className = "status-badge offline";
            }
        } catch (err) {
            statusBadge.textContent = "Offline";
            statusBadge.className = "status-badge offline";
        }
    }

    // Drop zone click triggers file picker
    if (dropZone && fileInput) {
        dropZone.addEventListener("click", () => fileInput.click());
        dropZone.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInput.click();
            }
        });

        // Drag and drop visual cues
        ["dragenter", "dragover"].forEach((eventName) => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove("dragover");
            });
        });
    }

    // Initial check
    checkStatus();
});
