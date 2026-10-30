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

    const textForm = document.getElementById("text-form");
    const textInput = document.getElementById("text-input");
    const textInbox = document.getElementById("text-inbox");
    const refreshTextBtn = document.getElementById("refresh-text-btn");

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
            loadTexts();
        } else {
            pairingCard.style.display = "block";
            filesList.innerHTML = "";
            const p = document.createElement("p");
            p.className = "empty-state";
            p.textContent = "Please pair your device to view shared files.";
            filesList.appendChild(p);

            textInbox.innerHTML = "";
            const pText = document.createElement("p");
            pText.className = "empty-state";
            pText.textContent = "Please pair your device to send and view text.";
            textInbox.appendChild(pText);
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

    // Submit pairing request with auto space/hyphen cleaning
    async function pairWithPin(rawPin) {
        if (!rawPin) return false;
        if (pairingError) {
            pairingError.classList.add("visually-hidden");
            pairingError.textContent = "";
        }

        // Clean spaces and hyphens commonly added by phone keyboards
        const pin = rawPin.replace(/[\s\-]/g, "").trim();
        if (!pin) return false;

        try {
            const res = await fetch("/api/auth/pair", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pin })
            });

            if (res.ok) {
                const data = await res.json();
                setAuthenticated(true, data.csrf_token);
                if (pairingPinInput) pairingPinInput.value = "";
                return true;
            } else {
                const err = await res.json().catch(() => ({}));
                if (pairingError) {
                    pairingError.textContent = err.detail || "Pairing failed. Check PIN.";
                    pairingError.classList.remove("visually-hidden");
                }
                return false;
            }
        } catch (err) {
            if (pairingError) {
                pairingError.textContent = "Could not reach server.";
                pairingError.classList.remove("visually-hidden");
            }
            return false;
        }
    }

    // Handle pairing submit
    if (pairingForm && pairingPinInput) {
        pairingForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            await pairWithPin(pairingPinInput.value);
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

        loadFiles();
    }

    function uploadSingleFile(file) {
        return new Promise((resolve) => {
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
                if (res.status === 401) setAuthenticated(false);
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
                nameDiv.textContent = file.filename;

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

    // Copy text with graceful clipboard fallback
    async function copyToClipboard(text, btnElement) {
        let success = false;
        // 1. Try modern navigator.clipboard if available
        if (navigator.clipboard && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(text);
                success = true;
            } catch {}
        }

        // 2. Fallback for plain HTTP / unsupported mobile browsers
        if (!success) {
            try {
                const ta = document.createElement("textarea");
                ta.value = text;
                ta.style.position = "fixed";
                ta.style.left = "-9999px";
                ta.style.top = "0";
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                success = document.execCommand("copy");
                document.body.removeChild(ta);
            } catch {}
        }

        if (success) {
            const orig = btnElement.textContent;
            btnElement.textContent = "Copied!";
            setTimeout(() => { btnElement.textContent = orig; }, 1500);
        } else {
            prompt("Copy snippet manually:", text);
        }
    }

    // Load and render text snippets
    async function loadTexts() {
        if (!isAuthenticated) return;

        try {
            const res = await fetch("/api/text");
            if (!res.ok) {
                if (res.status === 401) setAuthenticated(false);
                return;
            }

            const data = await res.json();
            textInbox.innerHTML = "";

            if (!data.messages || data.messages.length === 0) {
                const empty = document.createElement("p");
                empty.className = "empty-state";
                empty.textContent = "No text snippets yet.";
                textInbox.appendChild(empty);
                return;
            }

            data.messages.forEach((msg) => {
                const item = document.createElement("div");
                item.className = "text-item";

                const header = document.createElement("div");
                header.className = "text-header";

                const timeSpan = document.createElement("span");
                timeSpan.textContent = formatDate(msg.created_at);

                const actions = document.createElement("div");
                actions.className = "text-actions";

                const copyBtn = document.createElement("button");
                copyBtn.type = "button";
                copyBtn.className = "btn btn-sm btn-secondary";
                copyBtn.textContent = "Copy";
                copyBtn.addEventListener("click", () => copyToClipboard(msg.content, copyBtn));

                const delBtn = document.createElement("button");
                delBtn.type = "button";
                delBtn.className = "btn btn-sm btn-danger";
                delBtn.textContent = "Delete";
                delBtn.addEventListener("click", () => handleDeleteText(msg.id));

                actions.appendChild(copyBtn);
                actions.appendChild(delBtn);

                header.appendChild(timeSpan);
                header.appendChild(actions);

                const contentPre = document.createElement("pre");
                contentPre.className = "text-content";
                contentPre.textContent = msg.content; // Strict text rendering, safe against XSS

                item.appendChild(header);
                item.appendChild(contentPre);
                textInbox.appendChild(item);
            });
        } catch (err) {
            console.error("Failed to load text messages:", err);
        }
    }

    // Delete text snippet
    async function handleDeleteText(textId) {
        if (!confirm("Are you sure you want to delete this text snippet?")) {
            return;
        }

        try {
            const res = await fetch(`/api/text/${encodeURIComponent(textId)}`, {
                method: "DELETE",
                headers: {
                    ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {})
                }
            });

            if (res.ok) {
                loadTexts();
            } else {
                alert("Failed to delete text snippet.");
            }
        } catch {
            alert("Network error while deleting text snippet.");
        }
    }

    // Handle text submission
    if (textForm && textInput) {
        textForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!isAuthenticated) {
                alert("Please pair your device before sending text.");
                return;
            }

            const content = textInput.value;
            if (!content.trim()) return;

            try {
                const res = await fetch("/api/text", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {})
                    },
                    body: JSON.stringify({ content })
                });

                if (res.ok) {
                    textInput.value = "";
                    loadTexts();
                } else {
                    const err = await res.json().catch(() => ({}));
                    alert(err.detail || "Failed to send text snippet.");
                }
            } catch {
                alert("Network error while sending text.");
            }
        });
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

    if (refreshTextBtn) {
        refreshTextBtn.addEventListener("click", loadTexts);
    }

    // Initialization
    checkStatus();

    // Check for PIN in URL parameter (e.g. from QR code scan)
    const urlParams = new URLSearchParams(window.location.search);
    const pinParam = urlParams.get("pin") || urlParams.get("pair") || urlParams.get("token");
    if (pinParam) {
        // Strip pin from address bar for security and clean display
        try {
            const cleanUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, cleanUrl);
        } catch {}
        pairWithPin(pinParam);
    } else {
        checkAuth();
    }
});
