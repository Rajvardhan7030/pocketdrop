// PocketDrop Frontend Client — Vanilla JavaScript (No CDNs)

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const statusBadge = document.getElementById("connection-status");
    const pairingCard = document.getElementById("pairing-card");
    const pairingForm = document.getElementById("pairing-form");
    const pairingPinInput = document.getElementById("pairing-pin");
    const pairingError = document.getElementById("pairing-error");

    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadQueue = document.getElementById("upload-queue");

    const refreshFilesBtn = document.getElementById("refresh-files-btn");
    const filesList = document.getElementById("files-list");

    // State
    let csrfToken = null;
    let isAuthenticated = false;

    // Helper: format bytes
    function formatBytes(bytes) {
        if (bytes === 0) return "0 Bytes";
        const k = 1024;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
    }

    // Helper: format date
    function formatDate(dateStr) {
        if (!dateStr) return "";
        try {
            const d = new Date(dateStr);
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " " + d.toLocaleDateString();
        } catch {
            return dateStr;
        }
    }

    // Update pairing UI
    function setAuthenticated(auth, token) {
        isAuthenticated = auth;
        if (token) csrfToken = token;

        if (isAuthenticated) {
            pairingCard.style.display = "none";
            loadFiles();
        } else {
            pairingCard.style.display = "block";
            filesList.innerHTML = "";
            const p = document.createElement("p");
            p.className = "empty-state";
            p.textContent = "Please pair your device to view shared files.";
            filesList.appendChild(p);
        }
    }

    // Check auth status
    async function checkAuth() {
        try {
            const res = await fetch("/api/auth/check");
            if (res.ok) {
                const data = await res.json();
                setAuthenticated(data.authenticated, data.csrf_token);
            } else {
                setAuthenticated(false);
            }
        } catch {
            setAuthenticated(false);
        }
    }

    // Check server status
    async function checkStatus() {
        try {
            const res = await fetch("/api/status");
            if (res.ok) {
                statusBadge.textContent = "Online";
                statusBadge.className = "status-badge online";
            } else {
                statusBadge.textContent = "Error";
                statusBadge.className = "status-badge offline";
            }
        } catch {
            statusBadge.textContent = "Offline";
            statusBadge.className = "status-badge offline";
        }
    }

    // Handle pairing submit
    if (pairingForm) {
        pairingForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            pairingError.classList.add("visually-hidden");
            pairingError.textContent = "";

            const pin = pairingPinInput.value.trim();
            if (!pin) return;

            try {
                const res = await fetch("/api/auth/pair", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pin })
                });

                if (res.ok) {
                    const data = await res.json();
                    setAuthenticated(true, data.csrf_token);
                    pairingPinInput.value = "";
                } else {
                    const err = await res.json().catch(() => ({}));
                    pairingError.textContent = err.detail || "Pairing failed. Check PIN.";
                    pairingError.classList.remove("visually-hidden");
                }
            } catch (err) {
                pairingError.textContent = "Could not reach server.";
                pairingError.classList.remove("visually-hidden");
            }
        });
    }

    // File upload handler
    async function uploadFiles(files) {
        if (!isAuthenticated) {
            alert("Please pair your device before uploading files.");
            return;
        }

        if (!files || files.length === 0) return;

        for (let i = 0; i < files.length; i++) {
            await uploadSingleFile(files[i]);
        }

        // Refresh file list after upload batch
        loadFiles();
    }

    function uploadSingleFile(file) {
        return new Promise((resolve) => {
            // Create progress elements safely via DOM methods
            const progressItem = document.createElement("div");
            progressItem.className = "progress-item";

            const progressHeader = document.createElement("div");
            progressHeader.className = "progress-header";

            const nameSpan = document.createElement("span");
            nameSpan.textContent = file.name;

            const percentSpan = document.createElement("span");
            percentSpan.textContent = "0%";

            progressHeader.appendChild(nameSpan);
            progressHeader.appendChild(percentSpan);

            const progressBar = document.createElement("div");
            progressBar.className = "progress-bar";

            const progressFill = document.createElement("div");
            progressFill.className = "progress-fill";
            progressBar.appendChild(progressFill);

            progressItem.appendChild(progressHeader);
            progressItem.appendChild(progressBar);
            uploadQueue.appendChild(progressItem);

            const formData = new FormData();
            formData.append("files", file);

            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/api/uploads");

            if (csrfToken) {
                xhr.setRequestHeader("X-CSRF-Token", csrfToken);
            }

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = pct + "%";
                    percentSpan.textContent = pct + "%";
                }
            };

            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    percentSpan.textContent = "Uploaded";
                    progressFill.style.backgroundColor = "var(--success-text)";
                } else {
                    let errMsg = "Upload failed";
                    try {
                        const parsed = JSON.parse(xhr.responseText);
                        if (parsed.detail) errMsg = parsed.detail;
                    } catch {}
                    percentSpan.textContent = errMsg;
                    progressFill.style.backgroundColor = "var(--danger-color)";
                }
                setTimeout(() => {
                    if (progressItem.parentNode) {
                        progressItem.parentNode.removeChild(progressItem);
                    }
                    resolve();
                }, 1500);
            };

            xhr.onerror = () => {
                percentSpan.textContent = "Network error";
                progressFill.style.backgroundColor = "var(--danger-color)";
                setTimeout(() => {
                    if (progressItem.parentNode) {
                        progressItem.parentNode.removeChild(progressItem);
                    }
                    resolve();
                }, 2000);
            };

            xhr.send(formData);
        });
    }

    // Load and render shared files
    async function loadFiles() {
        if (!isAuthenticated) return;

        try {
            const res = await fetch("/api/files");
            if (!res.ok) {
                if (res.status === 401) {
                    setAuthenticated(false);
                }
                return;
            }

            const data = await res.json();
            filesList.innerHTML = "";

            if (!data.files || data.files.length === 0) {
                const empty = document.createElement("p");
                empty.className = "empty-state";
                empty.textContent = "No shared files yet.";
                filesList.appendChild(empty);
                return;
            }

            data.files.forEach((file) => {
                const item = document.createElement("div");
                item.className = "file-item";

                const infoDiv = document.createElement("div");
                infoDiv.className = "file-info";

                const nameDiv = document.createElement("div");
                nameDiv.className = "file-name";
                nameDiv.textContent = file.filename; // XSS-safe

                const metaDiv = document.createElement("div");
                metaDiv.className = "file-details";
                metaDiv.textContent = `${formatBytes(file.size_bytes)} • ${formatDate(file.created_at)}`;

                infoDiv.appendChild(nameDiv);
                infoDiv.appendChild(metaDiv);

                const actionsDiv = document.createElement("div");
                actionsDiv.className = "file-actions";

                const downloadLink = document.createElement("a");
                downloadLink.href = `/api/files/${encodeURIComponent(file.id)}`;
                downloadLink.download = file.filename;
                downloadLink.className = "btn btn-sm btn-secondary";
                downloadLink.textContent = "Download";

                const deleteBtn = document.createElement("button");
                deleteBtn.type = "button";
                deleteBtn.className = "btn btn-sm btn-danger";
                deleteBtn.textContent = "Delete";
                deleteBtn.addEventListener("click", () => handleDeleteFile(file.id, file.filename));

                actionsDiv.appendChild(downloadLink);
                actionsDiv.appendChild(deleteBtn);

                item.appendChild(infoDiv);
                item.appendChild(actionsDiv);
                filesList.appendChild(item);
            });
        } catch (err) {
            console.error("Failed to load files:", err);
        }
    }

    // Delete file confirmation
    async function handleDeleteFile(fileId, filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
            return;
        }

        try {
            const res = await fetch(`/api/files/${encodeURIComponent(fileId)}`, {
                method: "DELETE",
                headers: {
                    ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {})
                }
            });

            if (res.ok) {
                loadFiles();
            } else {
                alert("Failed to delete file.");
            }
        } catch {
            alert("Network error while deleting file.");
        }
    }

    // Drop zone events
    if (dropZone && fileInput) {
        dropZone.addEventListener("click", () => fileInput.click());
        dropZone.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInput.click();
            }
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                uploadFiles(e.target.files);
                fileInput.value = "";
            }
        });

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

        dropZone.addEventListener("drop", (e) => {
            if (e.dataTransfer && e.dataTransfer.files) {
                uploadFiles(e.dataTransfer.files);
            }
        });
    }

    if (refreshFilesBtn) {
        refreshFilesBtn.addEventListener("click", loadFiles);
    }

    // Initialization
    checkStatus();
    checkAuth();
});
