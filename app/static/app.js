const $ = (sel) => document.querySelector(sel);
let hls = null;
let statusInterval = null;

// --- Stream ---

function initStream() {
    const video = $("#video");
    const src = "/hls/live.m3u8";

    if (hls) {
        hls.destroy();
        hls = null;
    }

    if (Hls.isSupported()) {
        hls = new Hls({ liveSyncDurationCount: 3, liveMaxLatencyDurationCount: 5 });
        hls.loadSource(src);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
        hls.on(Hls.Events.ERROR, (_e, data) => {
            if (data.fatal) {
                $("#stream-status").textContent = "Stream error - retrying...";
                setTimeout(initStream, 3000);
            }
        });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = src;
        video.addEventListener("loadedmetadata", () => video.play());
    }
}

async function startStream() {
    $("#btn-stream-start").disabled = true;
    $("#stream-status").textContent = "Starting...";
    try {
        await fetch("/api/stream/start", { method: "POST" });
        // Wait for HLS segments to appear
        setTimeout(() => {
            initStream();
            $("#btn-stream-stop").disabled = false;
            $("#stream-status").textContent = "";
        }, 3000);
    } catch (e) {
        $("#stream-status").textContent = "Failed to start";
        $("#btn-stream-start").disabled = false;
    }
}

async function stopStream() {
    if (hls) { hls.destroy(); hls = null; }
    $("#video").src = "";
    await fetch("/api/stream/stop", { method: "POST" });
    $("#btn-stream-start").disabled = false;
    $("#btn-stream-stop").disabled = true;
    $("#stream-status").textContent = "";
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
        $("#stat-stream").textContent = s.running ? "Live" : "Off";
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

function formatSize(bytes) {
    if (!bytes) return "--";
    const n = parseInt(bytes, 10);
    if (isNaN(n)) return bytes;
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
    return (n / 1073741824).toFixed(2) + " GB";
}

async function fetchFiles() {
    const tbody = $("#files-body");
    tbody.innerHTML = "<tr><td colspan='3'>Loading...</td></tr>";
    try {
        const res = await fetch("/api/files");
        const data = await res.json();
        tbody.innerHTML = "";
        if (!data.files || data.files.length === 0) {
            tbody.innerHTML = "<tr><td colspan='3'>No files found</td></tr>";
            return;
        }
        for (const f of data.files) {
            const fpath = f.fpath || "";
            const name = fpath.split("\\").pop().split("/").pop() || fpath;
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="filename" data-path="${fpath}">${name}</td>
                <td>${formatSize(f.size)}</td>
                <td class="actions">
                    <button onclick="downloadFile('${fpath}')">Download</button>
                    <button class="danger" onclick="deleteFile('${fpath}', this)">Delete</button>
                </td>
            `;
            tr.querySelector(".filename").addEventListener("click", () => playFile(fpath));
            tbody.appendChild(tr);
        }
    } catch {
        tbody.innerHTML = "<tr><td colspan='3'>Failed to load files</td></tr>";
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
    const video = $("#video");
    if (hls) { hls.destroy(); hls = null; }
    video.src = `/api/files/download?path=${encodeURIComponent(path)}`;
    video.play();
}

// --- Init ---

document.addEventListener("DOMContentLoaded", () => {
    $("#btn-stream-start").addEventListener("click", startStream);
    $("#btn-stream-stop").addEventListener("click", stopStream);
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
