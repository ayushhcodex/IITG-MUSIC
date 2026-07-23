let currentDataset = null;
let currentPdbId = "1DMB";
let currentBmrbId = "";        // BMRB ID from the last successful fetch
let currentTimeline = [];
let viewer = null;
let activeResidueIndex = -1;
let presetsMap = {};
let isGenerating = false;
let pendingGenerate = false;   // true when a new dataset arrived while generation was in-progress
let noteBurstTimeout = null;
let isSpinning = false;
let spinAnimationId = null;

// ──────────────────────────────────────────────────────────────────────────
// Helper to get distinct music emoji based on Svara (note) or residue index
// ──────────────────────────────────────────────────────────────────────────
function getMusicEmojiForResidue(resiNum, svara) {
  if (svara) {
    const cleanSvara = svara.replace(/[0-9]/g, "").trim();
    const svaraMap = {
      "Sa": "🎵", "re": "🎶", "Re": "🎶", "ga": "🎼", "Ga": "🎼",
      "ma": "✨", "Ma": "✨", "Ma#": "✨", "pa": "🎧", "Pa": "🎧",
      "dha": "🎹", "Dha": "🎹", "ni": "🎻", "Ni": "🎻"
    };
    if (svaraMap[cleanSvara]) return svaraMap[cleanSvara];
  }
  const emojis = ["🎵", "🎶", "🎼", "✨", "🎧", "🎹", "🎻", "🪈"];
  return emojis[resiNum % emojis.length] || "🎵";
}

// ──────────────────────────────────────────────────────────────────────────
// Floating Music Note + Ribbon Pointer — update color & trigger animation
// whenever a new amino acid residue becomes active during playback
// ──────────────────────────────────────────────────────────────────────────
function updateFloatingNote(aaName, aaColor, activeCardIdx, emoji = "🎵") {
  const wrapper  = document.getElementById("floatingNoteWrapper");
  const note     = document.getElementById("floatingNote");
  const ripple   = document.getElementById("floatingNoteRipple");
  const pointer  = document.getElementById("ribbonNotePointer");
  const ribbon   = document.getElementById("sequenceRibbon");

  // ── 3D canvas floating note (if present) ──
  if (wrapper && note && ripple) {
    note.textContent      = emoji;
    note.style.color      = aaColor;
    note.style.textShadow = `0 0 18px ${aaColor}, 0 0 38px ${aaColor}`;
    ripple.style.borderColor = aaColor;

    wrapper.classList.add("note-active");

    note.classList.remove("note-burst");
    void note.offsetWidth;
    note.classList.add("note-burst");

    ripple.classList.remove("ripple-fire");
    void ripple.offsetWidth;
    ripple.classList.add("ripple-fire");

    if (noteBurstTimeout) clearTimeout(noteBurstTimeout);
    noteBurstTimeout = setTimeout(() => {
      note.classList.remove("note-burst");
      ripple.classList.remove("ripple-fire");
    }, 700);
  }

  // ── Ribbon strip pointer ──
  if (pointer && ribbon && activeCardIdx >= 0) {
    const activeCard = document.getElementById(`res-card-${activeCardIdx}`);
    if (activeCard) {
      const leftPx = activeCard.offsetLeft + (activeCard.offsetWidth / 2) - 8;
      pointer.style.left        = `${leftPx}px`;
      pointer.textContent       = emoji;
      pointer.style.color       = aaColor;
      pointer.style.textShadow  = `0 0 10px ${aaColor}`;
      pointer.classList.add("note-visible");
    }
  }
}

// 20 Standard Amino Acids Unique Vibrant Color Palette
const AMINO_ACID_COLORS = {
  // Positively Charged (Basic) — Vibrant Blues & Purples
  "LYS": "#00d2ff", // Neon Electric Blue
  "ARG": "#4facfe", // Bright Azure Blue
  "HIS": "#9d4edd", // Vivid Blue-Purple

  // Negatively Charged (Acidic) — Radiant Pinks & Crimson
  "ASP": "#ff0055", // Neon Crimson Pink
  "GLU": "#ff3864", // Rose Magenta

  // Hydrophobic / Aliphatic — Emeralds & Limes
  "ALA": "#00ff87", // Spring Lime Green
  "VAL": "#00e676", // Vivid Emerald Green
  "LEU": "#76ff03", // Chartreuse Neon
  "ILE": "#2ecc71", // Bright Jade Green
  "MET": "#1dd1a1", // Mint Turquoise
  "PRO": "#f39c12", // Amber Gold

  // Aromatic — Oranges & Warm Glows
  "PHE": "#ff9f43", // Bright Tangerine Orange
  "TYR": "#ff6b6b", // Coral Orange
  "TRP": "#ff3e00", // Scarlet Orange

  // Polar Uncharged — Cyans, Lavenders, Yellows
  "SER": "#00f2fe", // Bright Cyan
  "THR": "#48dbfb", // Sky Aqua Blue
  "ASN": "#feca57", // Bright Yellow
  "GLN": "#c56cf0", // Lavender Purple
  "CYS": "#fdd835", // Lemon Glow
  "GLY": "#ffffff"  // Crisp Pure White
};

function getAminoAcidColor(aa) {
  if (!aa) return "#00f2fe";
  const code = aa.toString().trim().toUpperCase();
  if (AMINO_ACID_COLORS[code]) {
    return AMINO_ACID_COLORS[code];
  }
  // Deterministic vibrant fallback for any modified or non-standard residue
  let hash = 0;
  for (let i = 0; i < code.length; i++) {
    hash = code.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 88%, 62%)`;
}

// Initialize application on load
window.addEventListener("DOMContentLoaded", () => {
  init3DViewer("1DMB");
  loadPresets();
  fetchOnlineData("25237");
  setupAudioListeners();
  setupKeyboardShortcuts();
});

// Switch Studio Tabs
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));
  
  const targetBtn = Array.from(document.querySelectorAll(".tab-btn")).find(btn => btn.getAttribute("onclick").includes(tabId));
  if (targetBtn) targetBtn.classList.add("active");
  
  const targetContent = document.getElementById(tabId);
  if (targetContent) targetContent.classList.add("active");
}

// Toggle Fullscreen Screen Recording Mode
function toggleRecordingMode() {
  document.body.classList.toggle("recording-mode");
  
  setTimeout(() => {
    if (viewer) {
      viewer.resize();
      viewer.render();
    }
  }, 120);
}

function setupKeyboardShortcuts() {
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && document.body.classList.contains("recording-mode")) {
      toggleRecordingMode();
    }
  });

  window.addEventListener("resize", () => {
    if (viewer) {
      viewer.resize();
      viewer.render();
    }
  });
}

// Toggle Continuous Clockwise Rotation of 3D Structure
function toggleStructureRotation() {
  const btn = document.getElementById("btnToggleSpin");
  isSpinning = !isSpinning;
  
  if (isSpinning) {
    if (btn) {
      btn.classList.add("spinning-active");
      btn.innerHTML = `<span>🔄 3D Motion: ON</span>`;
    }
    // Start smooth clockwise rotation around Y axis
    function step() {
      if (!isSpinning || !viewer) return;
      viewer.rotate(0.65, "y"); // 0.65 degrees per frame = smooth cinematic speed clockwise
      viewer.render();
      spinAnimationId = requestAnimationFrame(step);
    }
    spinAnimationId = requestAnimationFrame(step);
  } else {
    if (btn) {
      btn.classList.remove("spinning-active");
      btn.innerHTML = `<span>🔄 3D Motion: OFF</span>`;
    }
    if (spinAnimationId) cancelAnimationFrame(spinAnimationId);
  }
}

// Initialize 3Dmol.js viewer
function init3DViewer(pdbId) {
  const container = document.getElementById("mol3d");
  if (!container) return;
  container.innerHTML = "";
  
  viewer = $3Dmol.createViewer(container, {
    backgroundColor: "#090a12",
    id: "viewer3d"
  });
  
  load3DStructure(pdbId);
}

// Load 3D structure from PDB ID
function load3DStructure(pdbId) {
  if (!viewer) return;
  if (!pdbId || pdbId === "" || pdbId === "None") {
    viewer.clear();
    document.getElementById("molTitle").textContent = "Protein Structure (No PDB ID linked)";
    document.getElementById("molSubtitle").textContent = "Enter a 4-character PDB ID below to load coordinates.";
    const label = document.getElementById("currentPdbLabel");
    if (label) label.textContent = "None";
    viewer.render();
    return;
  }
  
  viewer.clear(); // Wipe existing models before loading new structure
  currentPdbId = pdbId.toUpperCase();
  const label = document.getElementById("currentPdbLabel");
  if (label) label.textContent = currentPdbId;
  document.getElementById("molTitle").textContent = `Protein Structure (PDB: ${currentPdbId})`;
  document.getElementById("molSubtitle").textContent = "Loading 3D molecular coordinates...";
  
  // multimodel: false ensures we only load Model 1 of NMR ensembles (preventing 20 stacked models!)
  $3Dmol.download("pdb:" + currentPdbId, viewer, { multimodel: false }, () => {
    // Style cartoon backbone colored by secondary structure across the loaded model
    viewer.setStyle({}, {
      cartoon: {
        colorfunc: (atom) => {
          if (atom.ss === "h") return "#00f2fe"; // Alpha helix
          if (atom.ss === "s") return "#f857a6"; // Beta sheet
          return "#f9d423"; // Random coil
        }
      }
    });
    viewer.zoomTo();
    viewer.render();
    document.getElementById("molSubtitle").textContent = "BioNMR IITG";
  }, (err) => {
    // If .pdb fails (e.g. mmCIF entry or network/404), try cif: fallback
    $3Dmol.download("cif:" + currentPdbId, viewer, { multimodel: false }, () => {
      viewer.setStyle({}, {
        cartoon: {
          colorfunc: (atom) => {
            if (atom.ss === "h") return "#00f2fe";
            if (atom.ss === "s") return "#f857a6";
            return "#f9d423";
          }
        }
      });
      viewer.zoomTo();
      viewer.render();
      document.getElementById("molSubtitle").textContent = "BioNMR IITG (mmCIF format)";
    }, (err2) => {
      document.getElementById("molSubtitle").textContent = `⚠️ Could not download 3D coordinates for PDB: ${currentPdbId}`;
    });
  });
}

function switch3DStructure() {
  const inputEl = document.getElementById("switchPdbInput");
  if (!inputEl) return;
  const val = inputEl.value.trim().toUpperCase();
  if (val.length === 4) {
    load3DStructure(val);
    inputEl.value = "";
  } else {
    alert("Please enter a valid 4-character PDB ID (e.g. 1DMB, 1ST7, 1CA2, 2MV0).");
  }
}

// Highlight single residue in 3D viewer with ball colored uniquely by Amino Acid + attach 3D music emoji label
function highlight3DResidue(resiNum, aaName, svara = "") {
  if (!viewer) return;
  const aaColor = getAminoAcidColor(aaName);
  const emoji = getMusicEmojiForResidue(resiNum, svara);

  let num = parseInt(resiNum, 10);
  let matchedAtoms = viewer.selectedAtoms({ resi: num });
  if (!matchedAtoms || matchedAtoms.length === 0) {
    matchedAtoms = viewer.selectedAtoms({ resi: String(resiNum) });
  }

  const targetChain = (matchedAtoms && matchedAtoms.length > 0) ? matchedAtoms[0].chain : "";
  const baseSelector = targetChain ? { chain: targetChain } : {};
  const resiSelector = targetChain ? { chain: targetChain, resi: num } : { resi: num };

  // Reset all styles to secondary structure color on target chain
  viewer.setStyle(baseSelector, {
    cartoon: {
      colorfunc: (atom) => {
        if (atom.ss === "h") return "#00f2fe";
        if (atom.ss === "s") return "#f857a6";
        return "#f9d423";
      }
    }
  });
  
  // Highlight currently sounding residue ONLY on primary chain so exactly ONE sphere appears!
  viewer.setStyle(resiSelector, {
    cartoon: { color: "#ffffff", thickness: 0.65 },
    sphere: { color: aaColor, radius: 2.15 }
  });

  // Attach crisp white music emoji right at the 3D sphere inside 3Dmol viewer!
  viewer.removeAllLabels();
  if (matchedAtoms && matchedAtoms.length > 0) {
    const centerAtom = matchedAtoms.find(a => a.atom === "CA" && (!targetChain || a.chain === targetChain)) || matchedAtoms[0];
    viewer.addLabel(emoji, {
      position: { x: centerAtom.x, y: centerAtom.y, z: centerAtom.z },
      fontColor: "#ffffff",
      backgroundColor: aaColor,
      fontSize: 20,
      borderThickness: 1.5,
      borderColor: "#ffffff",
      showBackground: true,
      inFront: true
    });
  }
  
  viewer.render();
}

// Load built-in presets
async function loadPresets() {
  try {
    const res = await fetch("/api/presets");
    const data = await res.json();
    presetsMap = data.presets;
    
    const container = document.getElementById("presetContainer");
    container.innerHTML = "";
    
    Object.keys(presetsMap).forEach(key => {
      const p = presetsMap[key];
      const card = document.createElement("div");
      card.className = "preset-card";
      card.innerHTML = `
        <h4>${p.title}</h4>
        <p>${p.description}</p>
      `;
      card.onclick = () => {
        document.getElementById("fetchInput").value = p.pdb_id;
        fetchOnlineData(p.pdb_id);
      };
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load presets", err);
  }
}

// Render initial sequence ribbon before audio generation completes
function renderInitialSequenceRibbon(dataset) {
  const ribbon = document.getElementById("sequenceRibbon");
  if (!ribbon) return;
  ribbon.innerHTML = "";

  dataset.forEach((item, idx) => {
    const card = document.createElement("div");
    let ssClass = "ss-coil";
    const ss = (item["Secondary Structure"] || item.secondary_structure || "").toLowerCase();
    if (ss.includes("helix")) ssClass = "ss-helix";
    else if (ss.includes("sheet") || ss.includes("beta")) ssClass = "ss-sheet";

    const seq = item.sequence || idx + 1;
    const aa = item.chem_comp_ID || item.amino_acid || "ALA";
    const aaColor = getAminoAcidColor(aa);

    card.className = `res-card ${ssClass}`;
    card.id = `res-card-${idx}`;
    card.innerHTML = `
      <div class="res-num">#${seq}</div>
      <div class="res-aa" style="color: ${aaColor}">${aa}</div>
      <div class="res-svara">Sa</div>
    `;
    card.onclick = () => {
      const emoji = getMusicEmojiForResidue(seq, "Sa");
      highlight3DResidue(seq, aa, "Sa");
      updateFloatingNote(aa, aaColor, idx, emoji);
      document.querySelectorAll(".res-card").forEach(c => {
        c.classList.remove("active-res");
        c.style.boxShadow = "";
        c.style.borderColor = "";
      });
      card.classList.add("active-res");
      card.style.boxShadow = `0 0 20px ${aaColor}`;
      card.style.borderColor = aaColor;
    };
    ribbon.appendChild(card);
  });
}

// Fetch protein online (BMRB / PDB)
async function fetchOnlineData(customId = null) {
  const inputId = customId || document.getElementById("fetchInput").value.trim() || "25237";
  try {
    const res = await fetch(`/api/fetch/${encodeURIComponent(inputId)}`);
    const data = await res.json();
    if (res.ok && data.status === "success") {
      currentDataset = data.rows;
      currentPdbId   = data.pdb_id;
      currentBmrbId  = data.bmrb_id || "";   // store BMRB ID for folder naming
      
      updateLoadedStatus(data.title, data.rows.length, data.csv_url, data.pdb_id);
      load3DStructure(data.pdb_id);
      
      if (data.spectrometer_mhz) {
        document.getElementById("spectroInput").value = data.spectrometer_mhz;
      }
      
      renderInitialSequenceRibbon(data.rows);
      
      // Auto render audio composition immediately so ribbon & player are ready to record
      generateMusic();
    } else {
      const errMsg = data.message || data.detail || "No NMR chemical shift data available.";
      alert("⚠️ " + errMsg);
      updateLoadedStatusError(errMsg);
    }
  } catch (err) {
    alert("Error fetching online protein data: " + err.message);
  }
}

// Upload CSV file
async function uploadCsvFile() {
  const fileInput = document.getElementById("csvFileInput");
  if (!fileInput.files || fileInput.files.length === 0) {
    alert("Please choose a CSV file first");
    return;
  }
  
  const pdbInput = document.getElementById("uploadPdbInput");
  const customPdb = pdbInput ? pdbInput.value.trim() : "";
  
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  if (customPdb.length === 4) {
    formData.append("pdb_id", customPdb);
  }
  
  const isRaw = document.getElementById("isRawPpmCheck") ? document.getElementById("isRawPpmCheck").checked : false;
  formData.append("is_raw_ppm", isRaw);
  
  try {
    const res = await fetch("/api/upload_csv", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      currentDataset = data.rows;
      currentPdbId   = data.pdb_id;
      currentBmrbId  = data.bmrb_id || "";   // may be empty for uploaded CSVs
      updateLoadedStatus(data.title, data.rows.length, data.csv_url, data.pdb_id);
      load3DStructure(data.pdb_id);
      renderInitialSequenceRibbon(data.rows);
      generateMusic();
    } else {
      alert("Error: " + (data.message || data.detail || "Failed to parse CSV"));
    }
  } catch (err) {
    alert("Upload failed: " + err.message);
  }
}

// Update loaded status badge
function updateLoadedStatus(title, count, csvUrl, pdbId = "") {
  const box = document.getElementById("loadedStatus");
  if (!box) return;
  box.style.display = "block";
  box.style.borderColor = "rgba(0, 242, 254, 0.4)";
  box.style.background = "rgba(9, 10, 18, 0.65)";
  document.getElementById("loadedTitle").textContent = `✅ ${title}`;
  document.getElementById("loadedSub").textContent = `${count} Amino Acid Residues loaded into Sequence Ribbon.`;
  
  const label = document.getElementById("currentPdbLabel");
  if (label) {
    label.textContent = (pdbId && pdbId !== "" && pdbId !== "None") ? pdbId.toUpperCase() : "None";
  }
  
  if (csvUrl) {
    const link = document.getElementById("linkDownloadCsv");
    if (link) {
      link.href = csvUrl;
      const prefix = currentBmrbId ? `BMRB_${currentBmrbId}` : (currentPdbId ? `PDB_${currentPdbId}` : `protein`);
      link.download = `${prefix}_dataset.csv`;
    }
  }
}

function updateLoadedStatusError(errMsg) {
  const box = document.getElementById("loadedStatus");
  if (!box) return;
  box.style.display = "block";
  box.style.borderColor = "rgba(255, 80, 80, 0.6)";
  box.style.background = "rgba(40, 10, 15, 0.75)";
  document.getElementById("loadedTitle").textContent = "❌ Data Retrieval Failed";
  document.getElementById("loadedSub").textContent = errMsg;
}

function autoRegenerateIfReady() {
  if (currentDataset && !isGenerating) {
    generateMusic();
  }
}

// Render Indian Classical Composition
async function generateMusic() {
  if (!currentDataset || currentDataset.length === 0) {
    return;
  }

  // If already generating, mark that we need to re-run once it finishes
  if (isGenerating) {
    pendingGenerate = true;
    return;
  }
  
  isGenerating = true;
  pendingGenerate = false;

  // Snapshot the dataset & PDB at the moment we start generating
  // so even if the user loads another protein mid-flight we re-run correctly.
  const snapshotDataset = currentDataset.slice();
  const snapshotPdbId  = currentPdbId;
  const snapshotBmrbId = currentBmrbId;

  const btn = document.getElementById("btnGenerate");
  const origText = btn.innerHTML;
  btn.innerHTML = "<span>⏳ Rendering Audio...</span>";
  btn.disabled = true;

  // Also disable the regenerate button if present
  const regenBtn = document.getElementById("btnRegen");
  if (regenBtn) regenBtn.disabled = true;
  
  const payload = {
    dataset:          snapshotDataset,
    spectrometer_mhz: parseFloat(document.getElementById("spectroInput").value) || 750.0,
    raag_name:        document.getElementById("raagSelect").value,
    root_note:        parseInt(document.getElementById("rootSelect").value),
    tempo_multiplier: floatVal(document.getElementById("tempoSelect").value),
    lead_inst:        parseInt(document.getElementById("leadSelect").value),
    echo_inst:        parseInt(document.getElementById("echoSelect").value || 74),
    accent_inst:      104,
    enable_drone:     true,
    enable_tabla:     true,
    pdb_id:           snapshotPdbId,
    bmrb_id:          snapshotBmrbId    // tells backend which protein folder to use
  };
  
  try {
    const res = await fetch("/api/sonify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    
    if (data.status === "success") {
      // Only update the UI if this generation matches the CURRENTLY loaded protein
      // (i.e., no newer protein was loaded while we were generating)
      if (!pendingGenerate) {
        currentTimeline = data.result.timeline;
        setupPlayer(data.audio_url, data.midi_url, data.csv_url);
        renderSequenceRibbon(currentTimeline);
        document.getElementById("currentSoundingBadge").textContent = "Residues Synced — Ready for Screen Recording";

        // Show folder save confirmation badge
        showRunSavedBadge(data.protein_folder, data.run_folder, data.timeline_url, data.final_freq_url, data.info_url);

      }
    }
  } catch (err) {
    console.error("Error rendering composition:", err);
  } finally {
    const btn = document.getElementById("btnGenerate");
    btn.innerHTML = origText;
    btn.disabled = false;
    isGenerating = false;

    // If a newer protein was loaded while we were generating, kick off a fresh run now
    if (pendingGenerate) {
      pendingGenerate = false;
      generateMusic();
    }
  }
}

// Show a small badge below the Generate button confirming where this run was saved.
function showRunSavedBadge(proteinFolder, runFolder, timelineUrl, finalFreqUrl, infoUrl) {
  let badge = document.getElementById("runSavedBadge");
  if (!badge) {
    badge = document.createElement("div");
    badge.id = "runSavedBadge";
    badge.style.cssText = [
      "margin-top: 0.5rem",
      "padding: 0.45rem 0.75rem",
      "border-radius: 8px",
      "background: rgba(0, 201, 167, 0.12)",
      "border: 1px solid rgba(0, 242, 254, 0.3)",
      "font-size: 0.78rem",
      "color: #a5f3e8",
      "line-height: 1.7"
    ].join(";");
    // Insert right after the generate button
    const genBtn = document.getElementById("btnGenerate");
    if (genBtn && genBtn.parentNode) {
      genBtn.parentNode.insertBefore(badge, genBtn.nextSibling);
    }
  }
  const linkStyle = "color:#00f2fe; text-decoration:none; font-weight:600;";
  const prefix = proteinFolder || "protein";
  
  let folderStr = "";
  if (proteinFolder && runFolder) {
      folderStr = `<br>📁 <code style="font-size:0.74rem; color:#e2e8f0">${proteinFolder}/${runFolder}/</code>`;
  }
  
  badge.innerHTML = [
    `<strong style="color:#00f2fe">💾 Run Saved</strong>`,
    folderStr,
    "<br>",
    finalFreqUrl ? `<a href="${finalFreqUrl}" download="${prefix}_final_frequencies.csv" style="${linkStyle}">⬇ final_frequencies.csv</a>` : "",
    finalFreqUrl ? " &nbsp; " : "",
    timelineUrl  ? `<a href="${timelineUrl}"  download="${prefix}_timeline.csv" style="${linkStyle}">⬇ timeline.csv</a>` : "",
    timelineUrl  ? " &nbsp; " : "",
    infoUrl      ? `<a href="${infoUrl}"      download="${prefix}_run_info.json" style="${linkStyle}">⬇ run_info.json</a>` : ""
  ].join("");
}

// Re-run sonification on the SAME already-loaded dataset.
// The existing randomness in sonify.py (duration choices + volume) means the
// WAV output will be novel each time even though the pitch order (Final_Freq
// → MIDI note → Raag quantization) follows the same scientific rules.
// The backend also overwrites the named {pdb_id}_dataset.csv after each run
// so the downloadable CSV always matches the music just generated.
async function regenerateMusic() {
  if (!currentDataset || currentDataset.length === 0) {
    alert("Please load a protein first before regenerating music.");
    return;
  }
  // Reuse the same generateMusic path — it picks up currentDataset & currentPdbId
  generateMusic();
}

function floatVal(v) {
  return parseFloat(v) || 1.0;
}

// Setup Audio Player UI
function setupPlayer(audioUrl, midiUrl, csvUrl) {
  const audio = document.getElementById("audioPlayer");
  audio.src = audioUrl;
  audio.load();
  
  const prefix = currentBmrbId ? `BMRB_${currentBmrbId}` : (currentPdbId ? `PDB_${currentPdbId}` : `protein`);
  
  const wavLink = document.getElementById("linkDownloadWav");
  if (wavLink) {
    wavLink.href = audioUrl;
    wavLink.download = `${prefix}_sonification.wav`;
  }
  
  const midLink = document.getElementById("linkDownloadMid");
  if (midLink) {
    midLink.href = midiUrl;
    midLink.download = `${prefix}_sonification.mid`;
  }
  
  const csvLink = document.getElementById("linkDownloadCsv");
  if (csvLink) {
    csvLink.href = csvUrl;
    csvLink.download = `${prefix}_dataset.csv`;
  }
}

// Render Sequence Ribbon
function renderSequenceRibbon(timeline) {
  const ribbon = document.getElementById("sequenceRibbon");
  if (!ribbon) return;
  ribbon.innerHTML = "";
  
  timeline.forEach((item, idx) => {
    const card = document.createElement("div");
    let ssClass = "ss-coil";
    if (item.secondary_structure.toLowerCase().includes("helix")) ssClass = "ss-helix";
    else if (item.secondary_structure.toLowerCase().includes("sheet") || item.secondary_structure.toLowerCase().includes("beta")) ssClass = "ss-sheet";
    
    const aaColor = getAminoAcidColor(item.amino_acid);

    card.className = `res-card ${ssClass}`;
    card.id = `res-card-${idx}`;
    card.innerHTML = `
      <div class="res-num">#${item.sequence}</div>
      <div class="res-aa" style="color: ${aaColor}">${item.amino_acid}</div>
      <div class="res-svara">${item.svara}</div>
    `;
    
    card.onclick = () => {
      const audio = document.getElementById("audioPlayer");
      audio.currentTime = item.time;
      audio.play();
      const emoji = getMusicEmojiForResidue(item.sequence, item.svara);
      highlight3DResidue(item.sequence, item.amino_acid, item.svara);
      updateFloatingNote(item.amino_acid, aaColor, idx, emoji);
      document.querySelectorAll(".res-card").forEach(c => {
        c.classList.remove("active-res");
        c.style.boxShadow = "";
        c.style.borderColor = "";
      });
      card.classList.add("active-res");
      card.style.boxShadow = `0 0 20px ${aaColor}`;
      card.style.borderColor = aaColor;
    };
    
    ribbon.appendChild(card);
  });
}

// Setup Audio listeners for syncing 3D structure & ribbon
function setupAudioListeners() {
  const audio = document.getElementById("audioPlayer");
  
  audio.addEventListener("timeupdate", () => {
    const cur = audio.currentTime;
    const dur = audio.duration || 1;
    
    const fill = document.getElementById("progressBarFill");
    fill.style.width = `${(cur / dur) * 100}%`;
    
    document.getElementById("currentTimeDisplay").textContent = formatTime(cur);
    document.getElementById("totalTimeDisplay").textContent = formatTime(dur);
    
    if (currentTimeline && currentTimeline.length > 0) {
      let foundIndex = -1;
      for (let i = 0; i < currentTimeline.length; i++) {
        const item = currentTimeline[i];
        if (cur >= item.time && cur <= item.time + item.duration) {
          foundIndex = i;
          break;
        }
      }
      
      if (foundIndex !== -1 && foundIndex !== activeResidueIndex) {
        activeResidueIndex = foundIndex;
        const activeItem = currentTimeline[foundIndex];
        const aaColor = getAminoAcidColor(activeItem.amino_acid);
        
        document.getElementById("currentSoundingBadge").innerHTML =
          `Residue #${activeItem.sequence} : <strong style="color: ${aaColor}">${activeItem.amino_acid}</strong> (${activeItem.secondary_structure}) — Svara: ${activeItem.svara} (${activeItem.final_freq} Hz)`;
          
        document.querySelectorAll(".res-card").forEach(c => {
          c.classList.remove("active-res");
          c.style.boxShadow = "";
          c.style.borderColor = "";
        });
        const activeCard = document.getElementById(`res-card-${foundIndex}`);
        if (activeCard) {
          activeCard.classList.add("active-res");
          activeCard.style.boxShadow = `0 0 20px ${aaColor}`;
          activeCard.style.borderColor = aaColor;
          
          const ribbon = document.getElementById("sequenceRibbon");
          if (ribbon) {
            const targetScroll = activeCard.offsetLeft - (ribbon.clientWidth / 2) + (activeCard.offsetWidth / 2);
            ribbon.scrollTo({ left: targetScroll, behavior: "smooth" });
          }
        }
        
        const emoji = getMusicEmojiForResidue(activeItem.sequence, activeItem.svara);
        highlight3DResidue(activeItem.sequence, activeItem.amino_acid, activeItem.svara);

        // 🎵 Animate floating music note + ribbon pointer in this AA's colour
        updateFloatingNote(activeItem.amino_acid, aaColor, foundIndex, emoji);
      }
    }
  });
  
  audio.addEventListener("ended", () => {
    document.getElementById("btnPlayPause").textContent = "▶";
    // Hide floating note and ribbon pointer when song ends
    const wrapper = document.getElementById("floatingNoteWrapper");
    const pointer = document.getElementById("ribbonNotePointer");
    if (wrapper) wrapper.classList.remove("note-active");
    if (pointer) pointer.classList.remove("note-visible");
    activeResidueIndex = -1;
  });
}

function togglePlayPause() {
  const audio = document.getElementById("audioPlayer");
  const btn = document.getElementById("btnPlayPause");
  if (audio.paused) {
    audio.play();
    btn.textContent = "⏸";
  } else {
    audio.pause();
    btn.textContent = "▶";
  }
}

function seekAudio(e) {
  const audio = document.getElementById("audioPlayer");
  if (!audio.duration) return;
  const container = e.currentTarget;
  const rect = container.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const ratio = clickX / rect.width;
  audio.currentTime = ratio * audio.duration;
}

function formatTime(s) {
  if (isNaN(s)) return "0:00";
  const mins = Math.floor(s / 60);
  const secs = Math.floor(s % 60);
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
}
