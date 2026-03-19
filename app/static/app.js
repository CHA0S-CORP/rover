const $ = (sel) => document.querySelector(sel);
let statusInterval = null;

// --- MJPEG Stream ---

function startMjpeg() {
    const img = $("#mjpeg");
    const overlay = $("#stream-overlay");
    img.src = "/api/stream/mjpeg?" + Date.now();
    img.onload = () => { overlay.classList.add("hidden"); };
    img.onerror = () => {
        overlay.textContent = "Stream error";
        overlay.classList.remove("hidden");
    };
    $("#btn-stream-start").disabled = true;
    $("#btn-stream-stop").disabled = false;
}

function stopMjpeg() {
    const img = $("#mjpeg");
    img.src = "";
    $("#stream-overlay").textContent = "Stream stopped";
    $("#stream-overlay").classList.remove("hidden");
    $("#btn-stream-start").disabled = false;
    $("#btn-stream-stop").disabled = true;
}

function takeSnapshot() {
    window.open("/api/stream/snapshot", "_blank");
}

// --- HLS ---

async function startHls() {
    $("#btn-hls-start").disabled = true;
    await fetch("/api/stream/hls/start", { method: "POST" });
    $("#btn-hls-stop").disabled = false;
    $("#stream-status").textContent = "HLS starting...";
    setTimeout(() => { $("#stream-status").textContent = ""; }, 5000);
}

async function stopHls() {
    await fetch("/api/stream/hls/stop", { method: "POST" });
    $("#btn-hls-start").disabled = false;
    $("#btn-hls-stop").disabled = true;
}

// --- Status polling ---

async function pollStatus() {
    try {
        const res = await fetch("/api/status");
        const s = await res.json();
        if (s.connected) {
            $("#conn-badge").textContent = "Connected";
            $("#conn-badge").className = "status-badge connected";
        } else {
            $("#conn-badge").textContent = "Disconnected";
            $("#conn-badge").className = "status-badge disconnected";
        }
        $("#stat-battery").textContent = s.battery || "--";
        $("#stat-space").textContent = s.free_space || "--";
        $("#stat-sd").textContent = s.sd_card || "--";
        const recSecs = s.recording_seconds || 0;
        $("#stat-recording").textContent = s.recording
            ? `${Math.floor(recSecs/60)}:${String(recSecs%60).padStart(2,"0")}`
            : "No";
    } catch {
        $("#conn-badge").textContent = "Disconnected";
        $("#conn-badge").className = "status-badge disconnected";
    }

    try {
        const res = await fetch("/api/stream/status");
        const s = await res.json();
        $("#stat-mjpeg").textContent = s.mjpeg_clients > 0 ? `${s.mjpeg_clients} viewer${s.mjpeg_clients > 1 ? "s" : ""}` : "Off";
        $("#stat-hls").textContent = s.hls_active ? (s.hls_ready ? "Ready" : "Starting") : "Off";
        $("#btn-hls-start").disabled = s.hls_active;
        $("#btn-hls-stop").disabled = !s.hls_active;
    } catch {}
}

// --- Camera controls ---

async function camAction(url, method = "POST", body = null) {
    try {
        const opts = { method };
        if (body) {
            opts.headers = { "Content-Type": "application/json" };
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(url, opts);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`Action ${url} failed:`, e);
        return null;
    }
}

// --- File browser ---

function formatSize(sizeStr) {
    if (!sizeStr || sizeStr === "--") return "--";
    // Camera returns human-readable like "260.0M"
    if (/[KMGT]$/i.test(sizeStr)) return sizeStr + "B";
    const n = parseInt(sizeStr, 10);
    if (isNaN(n)) return sizeStr;
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
    return (n / 1073741824).toFixed(2) + " GB";
}

async function fetchFiles() {
    const tbody = $("#files-body");
    tbody.innerHTML = "<tr><td colspan='5'>Loading...</td></tr>";
    try {
        const res = await fetch("/api/files");
        const data = await res.json();
        tbody.innerHTML = "";
        if (!data.files || data.files.length === 0) {
            tbody.innerHTML = "<tr><td colspan='5'>No files found</td></tr>";
            return;
        }
        for (const f of data.files) {
            const fpath = f.fpath || "";
            const name = f.name || fpath.split("/").pop();
            const camera = f.camera || "";
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="filename" data-path="${fpath}">${name}</td>
                <td>${camera}</td>
                <td>${formatSize(f.size)}</td>
                <td>${f.date || ""}</td>
                <td class="actions">
                    <button onclick="downloadFile('${fpath}')">Download</button>
                    <button class="danger" onclick="deleteFile('${fpath}', this)">Delete</button>
                </td>
            `;
            tr.querySelector(".filename").addEventListener("click", () => playFile(fpath));
            tbody.appendChild(tr);
        }
    } catch {
        tbody.innerHTML = "<tr><td colspan='5'>Failed to load files</td></tr>";
    }
}

function downloadFile(path) {
    window.open(`/api/files/download?path=${encodeURIComponent(path)}`, "_blank");
}

async function deleteFile(path, btn) {
    if (!confirm(`Delete ${path}?`)) return;
    btn.disabled = true;
    await fetch(`/api/files?path=${encodeURIComponent(path)}`, { method: "DELETE" });
    fetchFiles();
}

function playFile(path) {
    downloadFile(path);
}

// --- Init ---

document.addEventListener("DOMContentLoaded", () => {
    $("#btn-stream-start").addEventListener("click", startMjpeg);
    $("#btn-stream-stop").addEventListener("click", stopMjpeg);
    $("#btn-snapshot").addEventListener("click", takeSnapshot);
    $("#btn-hls-start").addEventListener("click", startHls);
    $("#btn-hls-stop").addEventListener("click", stopHls);
    $("#btn-rec-start").addEventListener("click", () => camAction("/api/record/start"));
    $("#btn-rec-stop").addEventListener("click", () => camAction("/api/record/stop"));
    $("#btn-photo").addEventListener("click", () => camAction("/api/photo"));
    $("#btn-mode").addEventListener("click", () => {
        camAction("/api/mode", "POST", { mode: parseInt($("#mode-select").value) });
    });
    $("#btn-refresh-files").addEventListener("click", fetchFiles);

    pollStatus();
    statusInterval = setInterval(pollStatus, 5000);
    fetchFiles();
});
