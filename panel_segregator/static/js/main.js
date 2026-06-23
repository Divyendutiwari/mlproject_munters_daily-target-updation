document.addEventListener("DOMContentLoaded", () => {
    const btnLoad = document.getElementById("btn-load");
    const btnOptimize = document.getElementById("btn-optimize");
    const btnDownload = document.getElementById("btn-download");
    const trackOriginal = document.getElementById("track-original");
    const trackOptimized = document.getElementById("track-optimized");
    const activeSheetDisplay = document.getElementById("active-sheet");
    const workTable = document.getElementById("work-table");
    const tableWrapper = document.getElementById("table-wrapper");
    const captureArea = document.getElementById("capture-area");
    
    // Zoom controls
    const btnZoomIn = document.getElementById("btn-zoom-in");
    const btnZoomOut = document.getElementById("btn-zoom-out");
    let currentZoom = 1;

    // Tooltip elements
    const tooltip = document.getElementById("panel-tooltip");
    const ttName = document.getElementById("tt-name");
    const ttDim = document.getElementById("tt-dim");
    const ttType = document.getElementById("tt-type");
    
    let originalData = [];
    let optimizedData = [];

    // Table settings
    const TABLE_SIZE = 600; // Updated from CSS
    const MAX_REAL_SIZE = 2400; 
    const SCALE = TABLE_SIZE / MAX_REAL_SIZE;

    btnLoad.addEventListener("click", loadData);
    btnOptimize.addEventListener("click", () => {
        renderQueue(optimizedData, trackOptimized);
        btnOptimize.disabled = true;
        simulate3DMachine(optimizedData);
    });

    // Zoom Logic
    function applyZoom() {
        tableWrapper.style.transform = `scale(${currentZoom})`;
    }
    btnZoomIn.addEventListener("click", () => { currentZoom = Math.min(currentZoom + 0.2, 3); applyZoom(); });
    btnZoomOut.addEventListener("click", () => { currentZoom = Math.max(currentZoom - 0.2, 0.5); applyZoom(); });
    
    // Mouse wheel zoom on table
    captureArea.addEventListener('wheel', (e) => {
        if (e.deltaY < 0) currentZoom = Math.min(currentZoom + 0.1, 3);
        else currentZoom = Math.max(currentZoom - 0.1, 0.5);
        applyZoom();
        e.preventDefault();
    }, {passive: false});

    // Download Logic
    btnDownload.addEventListener("click", () => {
        // Hide zoom buttons and tooltip for capture
        document.querySelector('.zoom-controls').style.display = 'none';
        tooltip.classList.remove('visible');
        
        html2canvas(captureArea, { backgroundColor: null }).then(canvas => {
            const link = document.createElement('a');
            link.download = 'panel_segregation_pyramid.png';
            link.href = canvas.toDataURL();
            link.click();
            
            // Restore UI
            document.querySelector('.zoom-controls').style.display = 'flex';
        });
    });

    async function loadData() {
        btnLoad.disabled = true;
        btnLoad.textContent = "Loading...";
        
        try {
            const response = await fetch("/api/optimize-sequence");
            const data = await response.json();
            
            if (data.status === "success") {
                originalData = data.original_queue;
                optimizedData = data.optimized_queue;
                
                renderQueue(originalData, trackOriginal);
                btnOptimize.disabled = false;
                btnLoad.textContent = "Data Loaded (80 Sheets)";
                btnLoad.style.backgroundColor = "var(--success)";
            } else {
                alert("Error: " + data.error);
                btnLoad.disabled = false;
                btnLoad.textContent = "Load 80+ Sheets";
            }
        } catch (e) {
            console.error(e);
            alert("Failed to connect to backend");
            btnLoad.disabled = false;
            btnLoad.textContent = "Load 80+ Sheets";
        }
    }

    function renderQueue(data, container) {
        container.innerHTML = "";
        data.forEach((sheet, idx) => {
            const card = document.createElement("div");
            card.className = "sheet-card";
            card.id = `${container.id}-sheet-${idx}`;
            
            card.innerHTML = `
                <div class="sheet-id">${sheet['Sheet ID']}</div>
                <div class="sheet-trait">${sheet['Dominant Size']}</div>
                <div style="font-size:0.65rem; color:#94a3b8; margin-top:4px;">${sheet['Total Panels']} Panels</div>
            `;
            container.appendChild(card);
        });
    }

    function simulate3DMachine(queue) {
        const tl = gsap.timeline({
            onComplete: () => {
                activeSheetDisplay.innerHTML = `<h3>Queue Complete</h3><p>Perfect 3D Pyramid Achieved</p>`;
                activeSheetDisplay.style.color = "var(--success)";
                btnDownload.style.display = "inline-block"; // Show download button at the end
            }
        });
        
        workTable.innerHTML = "";
        
        let globalDelay = 0;
        let stackZIndex = 0;
        
        // Track the highest "layer" so far to know when to bump Z index
        let currentLayerArea = 0; 

        queue.forEach((sheet, sheetIdx) => {
            
            tl.call(() => {
                document.querySelectorAll('.sheet-card').forEach(c => c.classList.remove('active-punch'));
                const card = document.getElementById(`track-optimized-sheet-${sheetIdx}`);
                if(card) {
                    card.classList.add('active-punch');
                    // Prevent vertical page scroll, just scroll the container horizontally
                    card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
                }
                
                activeSheetDisplay.innerHTML = `
                    <p>Processing</p>
                    <h3>${sheet['Sheet ID']}</h3>
                    <p style="font-size:0.75rem; color:#f59e0b; margin-top:4px;">Max Area: ${sheet['Max Panel Area']} sqm</p>
                `;
            }, null, globalDelay);

            const panels = sheet['Panels'];
            panels.sort((a,b) => b.Area - a.Area);
            
            // Side-by-side logic: We group smaller panels in pairs
            let pendingSmallPanel = null;
            
            panels.forEach((p, pIdx) => {
                tl.call(() => {
                    const div = document.createElement("div");
                    div.className = `panel-3d ${p.Type}`;
                    
                    const w = p.Length * SCALE;
                    const h = p.Width * SCALE;
                    
                    div.style.width = `${w}px`;
                    div.style.height = `${h}px`;
                    
                    let xOffset = -50;
                    let yOffset = -50;
                    
                    // Logic to stack two panels side-by-side if they are small enough
                    // If the width is < 40% of the table (meaning we can easily fit two)
                    if (w < (TABLE_SIZE * 0.45)) {
                        if (pendingSmallPanel) {
                            // We already have a small panel on the left, put this one on the right
                            xOffset = 5; // offset slightly right
                            pendingSmallPanel = null;
                            // Don't increase stackZIndex because it sits next to the previous one!
                        } else {
                            // Put this one on the left and mark it as pending
                            xOffset = -105; // offset slightly left
                            pendingSmallPanel = true;
                            stackZIndex++; // It starts a new layer
                        }
                    } else {
                        // Large panel, clear pending state and stack normally centered
                        pendingSmallPanel = null;
                        stackZIndex++;
                    }
                    
                    const elevation = stackZIndex * 5; 
                    workTable.appendChild(div);
                    
                    div.addEventListener("mouseenter", () => {
                        ttName.textContent = p['Part Name'];
                        ttDim.textContent = `${p.Length}mm x ${p.Width}mm`;
                        ttType.textContent = p.Type;
                        ttType.style.backgroundColor = p.Type === "Thermal" ? "#f59e0b" : "#3b82f6";
                        tooltip.classList.add("visible");
                    });
                    
                    div.addEventListener("mouseleave", () => {
                        tooltip.classList.remove("visible");
                    });
                    
                    gsap.fromTo(div, 
                        { xPercent: xOffset, yPercent: yOffset, z: elevation + 800, opacity: 0 },
                        { xPercent: xOffset, yPercent: yOffset, z: elevation, opacity: 1, duration: 0.3, ease: "bounce.out" }
                    );
                }, null, globalDelay + 0.3 + (pIdx * 0.15)); 
            });
            
            globalDelay += 0.3 + (panels.length * 0.15) + 0.1;
        });
    }
});
