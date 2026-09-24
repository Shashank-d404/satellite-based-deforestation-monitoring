(() => {
    "use strict";

    const API = "";

    const YEARS = Array.from(
        { length: 11 },
        (_, index) => 2016 + index
    );

    const STORAGE = {
        theme: "forest-monitor-theme",
        reports: "forest-monitor-reports",
        communities: "forest-monitor-communities",
        newsletter: "forest-monitor-newsletter"
    };

    const state = {
        map: null,
        mapInitialBounds: null,
        marker: null,
        activeAnalysis: null,
        searchResults: [],
        layers: {
            baseline: null,
            current: null,
            change: null,
            loss: null
        }
    };

    const seededCommunities = [
        {
            id: "bengaluru-green-watch",
            name: "Bengaluru Green Watch",
            location: "Bengaluru",
            focus: "forest",
            description:
                "Community space for sharing observations about forest cover, vegetation change and urban green corridors.",
            members: 124,
            posts: 31,
            joined: false
        },
        {
            id: "western-ghats-guardians",
            name: "Western Ghats Guardians",
            location: "Western Ghats",
            focus: "forest",
            description:
                "A monitoring-focused community for conservation observations and potential vegetation-loss signals.",
            members: 87,
            posts: 19,
            joined: false
        },
        {
            id: "urban-water-watch",
            name: "Urban Water Watch",
            location: "South India",
            focus: "water",
            description:
                "Share local water-resource observations and connect field reports with mapped environmental context.",
            members: 63,
            posts: 15,
            joined: false
        }
    ];

    const $ = (selector, root = document) =>
        root.querySelector(selector);

    const $$ = (selector, root = document) =>
        Array.from(root.querySelectorAll(selector));

    function escapeHTML(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatNumber(value) {
        if (
            value === null ||
            value === undefined ||
            value === "" ||
            Number.isNaN(Number(value))
        ) {
            return "—";
        }

        return new Intl.NumberFormat("en-IN").format(Number(value));
    }

    function formatDecimal(value, digits = 4) {
        if (
            value === null ||
            value === undefined ||
            value === "" ||
            Number.isNaN(Number(value))
        ) {
            return "—";
        }

        return Number(value).toFixed(digits);
    }

    /* =========================================================
       TOAST
    ========================================================= */

    function showToast(message, kind = "success") {
        const toast = $("#toast");
        const messageElement = $("#toastMessage");
        const icon = $(".toast-icon i", toast);

        if (!toast || !messageElement) {
            return;
        }

        messageElement.textContent = message;

        icon.className =
            kind === "error"
                ? "fa-solid fa-triangle-exclamation"
                : kind === "info"
                ? "fa-solid fa-circle-info"
                : "fa-solid fa-check";

        toast.classList.add("show");

        clearTimeout(showToast.timer);

        showToast.timer = setTimeout(() => {
            toast.classList.remove("show");
        }, 3200);
    }

    /* =========================================================
       ANALYSIS STATUS
    ========================================================= */

    function setAnalysisStatus(label, busy = false) {
        const box = $("#analysisStatus");

        if (!box) {
            return;
        }

        box.innerHTML = `
            <span class="status-dot"></span>
            <span>${escapeHTML(label)}</span>
        `;

        box.classList.toggle("busy", busy);
    }

    /* =========================================================
       MODALS
    ========================================================= */

    function openModal(id) {
        const modal = document.getElementById(id);

        if (!modal) {
            return;
        }

        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal(id) {
        const modal = document.getElementById(id);

        if (!modal) {
            return;
        }

        modal.hidden = true;

        if (!$$(".modal-backdrop:not([hidden])").length) {
            document.body.style.overflow = "";
        }
    }

    function setupModalHandlers() {
        $$("[data-close-modal]").forEach(button => {
            button.addEventListener("click", () => {
                closeModal(button.dataset.closeModal);
            });
        });

        $$(".modal-backdrop").forEach(modal => {
            modal.addEventListener("click", event => {
                if (event.target === modal) {
                    closeModal(modal.id);
                }
            });
        });

        document.addEventListener("keydown", event => {
            if (event.key !== "Escape") {
                return;
            }

            $$(".modal-backdrop:not([hidden])").forEach(modal => {
                closeModal(modal.id);
            });
        });
    }

    /* =========================================================
       THEME
    ========================================================= */

    function setupTheme() {
        const savedTheme = localStorage.getItem(STORAGE.theme);

        if (savedTheme === "dark") {
            document.body.classList.add("dark-theme");
        }

        updateThemeIcon();

        $("#themeToggle")?.addEventListener("click", () => {
            document.body.classList.toggle("dark-theme");

            localStorage.setItem(
                STORAGE.theme,
                document.body.classList.contains("dark-theme")
                    ? "dark"
                    : "light"
            );

            updateThemeIcon();
        });
    }

    function updateThemeIcon() {
        const icon = $("#themeToggle i");

        if (!icon) {
            return;
        }

        icon.className = document.body.classList.contains("dark-theme")
            ? "fa-solid fa-sun"
            : "fa-solid fa-moon";
    }

    /* =========================================================
       NAVIGATION
    ========================================================= */

    function setupNavigation() {
        const nav = $("#mainNav");
        const toggle = $("#mobileMenuToggle");

        toggle?.addEventListener("click", () => {
            const open = nav.classList.toggle("open");

            toggle.setAttribute(
                "aria-expanded",
                String(open)
            );

            toggle.innerHTML = open
                ? '<i class="fa-solid fa-xmark"></i>'
                : '<i class="fa-solid fa-bars"></i>';
        });

        $$(".nav-link").forEach(link => {
            link.addEventListener("click", () => {
                nav?.classList.remove("open");

                if (toggle) {
                    toggle.setAttribute(
                        "aria-expanded",
                        "false"
                    );

                    toggle.innerHTML =
                        '<i class="fa-solid fa-bars"></i>';
                }
            });
        });

        const sections = $$("main section[id]");

        const observer = new IntersectionObserver(
            entries => {
                const visible = entries
                    .filter(entry => entry.isIntersecting)
                    .sort(
                        (a, b) =>
                            b.intersectionRatio -
                            a.intersectionRatio
                    )[0];

                if (!visible) {
                    return;
                }

                $$(".nav-link").forEach(link => {
                    link.classList.toggle(
                        "active",
                        link.getAttribute("href") ===
                            `#${visible.target.id}`
                    );
                });
            },
            {
                rootMargin: "-30% 0px -55% 0px",
                threshold: [0.05, 0.2, 0.4]
            }
        );

        sections.forEach(section => {
            observer.observe(section);
        });
    }

    /* =========================================================
       SCROLL
    ========================================================= */

    function setupScrollControls() {
        const backToTop = $("#backToTop");

        window.addEventListener(
            "scroll",
            () => {
                backToTop?.classList.toggle(
                    "visible",
                    window.scrollY > 550
                );
            },
            { passive: true }
        );

        backToTop?.addEventListener("click", () => {
            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });
        });
    }

    /* =========================================================
       YEARS
    ========================================================= */

    function populateYears() {
        const baseline = $("#baselineYear");
        const current = $("#currentYear");

        if (!baseline || !current) {
            return;
        }

        YEARS.forEach(year => {
            baseline.appendChild(
                new Option(String(year), String(year))
            );

            current.appendChild(
                new Option(String(year), String(year))
            );
        });

        baseline.value = "2025";
        current.value = "2026";

        baseline.addEventListener(
            "change",
            enforceYearOrder
        );

        current.addEventListener(
            "change",
            enforceYearOrder
        );
    }

    function enforceYearOrder() {
        let baseline = Number(
            $("#baselineYear").value
        );

        let current = Number(
            $("#currentYear").value
        );

        if (baseline >= current) {
            if (baseline < 2026) {
                $("#currentYear").value = String(
                    Math.min(baseline + 1, 2026)
                );
            } else {
                $("#baselineYear").value = String(
                    Math.max(current - 1, 2016)
                );
            }
        }

        $("#summaryPeriod").textContent =
            `${$("#baselineYear").value} → ${$("#currentYear").value}`;
    }

    /* =========================================================
       URL HELPERS
    ========================================================= */

    function absoluteUrl(url) {
        if (!url) {
            return null;
        }

        if (/^https?:\/\//i.test(url)) {
            return url;
        }

        return `${API}${
            url.startsWith("/")
                ? url
                : `/${url}`
        }`;
    }

    function getLayerUrl(metadata, names) {
        const layers =
            metadata?.layers ||
            metadata?.visuals ||
            metadata?.layer_urls ||
            {};

        for (const name of names) {
            const value = layers[name];

            if (
                typeof value === "string" &&
                value
            ) {
                return value;
            }

            if (
                value &&
                typeof value === "object"
            ) {
                if (
                    typeof value.url ===
                    "string"
                ) {
                    return value.url;
                }

                if (
                    typeof value.path ===
                    "string"
                ) {
                    return value.path;
                }
            }
        }

        return null;
    }

    /* =========================================================
       LEAFLET MAP
    ========================================================= */

    function initializeMap() {
        if (
            !window.L ||
            !$("#map")
        ) {
            return;
        }

        state.map = L.map("map", {
            zoomControl: true,
            attributionControl: true
        });

        const street = L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,
                attribution:
                    "&copy; OpenStreetMap contributors"
            }
        );

        const imagery = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            {
                maxZoom: 19,
                attribution:
                    "Tiles &copy; Esri"
            }
        );

        street.addTo(state.map);

        L.control
            .layers(
                {
                    Street: street,
                    "Satellite imagery": imagery
                },
                {},
                {
                    collapsed: true
                }
            )
            .addTo(state.map);

        state.map.setView(
            [12.167, 75.49],
            9
        );
    }

    function clearLayers() {
        Object.values(state.layers).forEach(layer => {
            if (
                layer &&
                state.map?.hasLayer(layer)
            ) {
                state.map.removeLayer(layer);
            }
        });

        state.layers = {
            baseline: null,
            current: null,
            change: null,
            loss: null
        };
    }

    function addImageOverlay(
        url,
        bounds,
        opacity = 0.78
    ) {
        if (
            !url ||
            !state.map ||
            !bounds
        ) {
            return null;
        }

        const layer = L.imageOverlay(
            url,
            bounds,
            {
                opacity,
                interactive: false,
                crossOrigin: true
            }
        );

        layer.addTo(state.map);

        return layer;
    }

    function setLayerVisibility(
        key,
        visible
    ) {
        const layer = state.layers[key];

        if (
            !layer ||
            !state.map
        ) {
            return;
        }

        if (
            visible &&
            !state.map.hasLayer(layer)
        ) {
            layer.addTo(state.map);
        }

        if (
            !visible &&
            state.map.hasLayer(layer)
        ) {
            state.map.removeLayer(layer);
        }
    }

    function bindLayerToggles() {
        [
            ["layerBaseline", "baseline"],
            ["layerCurrent", "current"],
            ["layerChange", "change"],
            ["layerLoss", "loss"]
        ].forEach(([id, key]) => {
            $(`#${id}`)?.addEventListener(
                "change",
                event => {
                    setLayerVisibility(
                        key,
                        event.target.checked
                    );
                }
            );
        });
    }

    function normalizeBounds(metadata) {
        const bounds =
            metadata?.bounds ||
            metadata?.bbox ||
            metadata?.map_bounds;

        if (!Array.isArray(bounds)) {
            return null;
        }

        if (
            bounds.length === 2 &&
            Array.isArray(bounds[0]) &&
            Array.isArray(bounds[1])
        ) {
            return [
                [
                    Number(bounds[0][0]),
                    Number(bounds[0][1])
                ],
                [
                    Number(bounds[1][0]),
                    Number(bounds[1][1])
                ]
            ];
        }

        if (
            bounds.length >= 4 &&
            bounds.every(value =>
                Number.isFinite(
                    Number(value)
                )
            )
        ) {
            return [
                [
                    Number(bounds[1]),
                    Number(bounds[0])
                ],
                [
                    Number(bounds[3]),
                    Number(bounds[2])
                ]
            ];
        }

        return null;
    }

    /* =========================================================
       POTENTIAL LOSS GEOJSON
    ========================================================= */

    async function loadPotentialLoss(
        pair,
        bounds
    ) {
        if (!state.map) {
            return;
        }

        try {
            const response = await fetch(
                `${API}/dynamic/${encodeURIComponent(
                    pair
                )}/potential_loss.geojson`
            );

            if (!response.ok) {
                return;
            }

            const data =
                await response.json();

            if (
                !Array.isArray(
                    data?.features
                )
            ) {
                return;
            }

            const layer = L.geoJSON(
                data,
                {
                    style: {
                        color: "#ff7676",
                        weight: 1.4,
                        fillColor: "#ff5a5f",
                        fillOpacity: 0.55
                    },

                    onEachFeature:
                        (
                            feature,
                            featureLayer
                        ) => {
                            const properties =
                                feature?.properties ||
                                {};

                            featureLayer.bindPopup(`
                                <strong>
                                    ${escapeHTML(
                                        properties.label ||
                                            properties.region ||
                                            "Potential loss region"
                                    )}
                                </strong>
                                <br>
                                <span>
                                    Potential vegetation-loss screening area.
                                </span>
                            `);
                        }
                }
            );

            state.layers.loss = layer;

            if (
                $("#layerLoss")?.checked
            ) {
                layer.addTo(state.map);
            }

            if (bounds) {
                state.map.fitBounds(
                    bounds,
                    {
                        padding: [20, 20]
                    }
                );
            }
        } catch (error) {
            console.debug(
                "Potential-loss GeoJSON unavailable",
                error
            );
        }
    }

    /* =========================================================
       UPDATE MAP
    ========================================================= */

    function updateMap(metadata) {
        if (!state.map) {
            return;
        }

        clearLayers();

        const bounds =
            normalizeBounds(metadata);

        if (bounds) {
            state.mapInitialBounds =
                bounds;

            state.map.fitBounds(
                bounds,
                {
                    padding: [18, 18]
                }
            );
        }

        const baseline = Number(
            $("#baselineYear").value
        );

        const current = Number(
            $("#currentYear").value
        );

        state.layers.baseline =
            addImageOverlay(
                absoluteUrl(
                    getLayerUrl(
                        metadata,
                        [
                            "baseline_ndvi",
                            "ndvi_baseline",
                            `ndvi_${baseline}`,
                            "baseline"
                        ]
                    )
                ),
                bounds,
                0.78
            );

        state.layers.current =
            addImageOverlay(
                absoluteUrl(
                    getLayerUrl(
                        metadata,
                        [
                            "current_ndvi",
                            "ndvi_current",
                            `ndvi_${current}`,
                            "current"
                        ]
                    )
                ),
                bounds,
                0.78
            );

        state.layers.change =
            addImageOverlay(
                absoluteUrl(
                    getLayerUrl(
                        metadata,
                        [
                            "ndvi_change",
                            "change",
                            "ndvi_delta"
                        ]
                    )
                ),
                bounds,
                0.84
            );

        [
            ["baseline", "layerBaseline"],
            ["current", "layerCurrent"],
            ["change", "layerChange"]
        ].forEach(([key, id]) => {
            setLayerVisibility(
                key,
                $(`#${id}`)?.checked ?? true
            );
        });

        loadPotentialLoss(
            `${baseline}_${current}`,
            bounds
        );
    }

    /* =========================================================
       RENDER ANALYSIS STATS
    ========================================================= */

    function renderStats(metadata) {
        const stats =
            metadata?.statistics ||
            metadata?.stats ||
            metadata ||
            {};

        const common =
            stats.common ||
            stats.common_valid ||
            {};

        const mean =
            stats.mean_ndvi_change ??
            stats.mean_change ??
            common.mean_ndvi_change;

        const loss =
            stats.loss_pixels ??
            stats.potential_loss_pixels ??
            stats.deforestation_pixels;

        const share =
            stats.loss_share ??
            stats.potential_loss_share ??
            stats.deforestation_share;

        const valid =
            stats.valid_common_pixels ??
            stats.common_valid_pixels ??
            stats.valid_pixels ??
            common.valid_pixels;

        const min =
            stats.min_ndvi_change ??
            stats.min_change;

        const max =
            stats.max_ndvi_change ??
            stats.max_change;

        const regions =
            stats.detected_regions ??
            stats.regions ??
            metadata?.detected_regions;

        $("#meanChange").textContent =
            mean === undefined
                ? "—"
                : formatDecimal(mean, 4);

        $("#lossPixels").textContent =
            loss === undefined
                ? "—"
                : formatNumber(loss);

        $("#lossShare").textContent =
            share === undefined
                ? "—"
                : `${Number(share).toFixed(2)}%`;

        $("#validPixels").textContent =
            valid === undefined
                ? "—"
                : formatNumber(valid);

        $("#detectedRegions").textContent =
            regions === undefined
                ? "—"
                : formatNumber(regions);

        $("#ndviRange").textContent =
            min !== undefined &&
            max !== undefined
                ? `${formatDecimal(
                      min,
                      3
                  )} to ${formatDecimal(
                      max,
                      3
                  )}`
                : "—";

        $("#resultChip").textContent =
            metadata
                ? "Calculated"
                : "Pending";
    }

    /* =========================================================
       SCENE INFO
    ========================================================= */

    function renderSceneInfo(metadata) {
        const baseline =
            metadata?.baseline_scene ||
            metadata?.baseline ||
            {};

        const current =
            metadata?.current_scene ||
            metadata?.current ||
            {};

        const baselineDate =
            baseline.date ||
            baseline.acquired ||
            baseline.datetime ||
            baseline.scene_date;

        const currentDate =
            current.date ||
            current.acquired ||
            current.datetime ||
            current.scene_date;

        const baselineCloud =
            baseline.cloud_cover ??
            baseline.cloud ??
            baseline.cloud_percentage;

        const currentCloud =
            current.cloud_cover ??
            current.cloud ??
            current.cloud_percentage;

        $("#baselineSceneDate").textContent =
            baselineDate
                ? String(
                      baselineDate
                  ).slice(0, 10)
                : "Baseline scene";

        $("#currentSceneDate").textContent =
            currentDate
                ? String(
                      currentDate
                  ).slice(0, 10)
                : "Current scene";

        $("#baselineSceneCloud").textContent =
            baselineCloud === undefined
                ? "Cloud data unavailable"
                : `${Number(
                      baselineCloud
                  ).toFixed(
                      2
                  )}% cloud cover`;

        $("#currentSceneCloud").textContent =
            currentCloud === undefined
                ? "Cloud data unavailable"
                : `${Number(
                      currentCloud
                  ).toFixed(
                      2
                  )}% cloud cover`;

        if (
            baselineCloud !== undefined &&
            currentCloud !== undefined
        ) {
            const maxCloud = Math.max(
                Number(baselineCloud),
                Number(currentCloud)
            );

            $("#qualityPill").textContent =
                `${maxCloud.toFixed(
                    1
                )}% max cloud`;

            $("#heroCloudStat").textContent =
                `${maxCloud.toFixed(
                    1
                )}% max`;
        }
    }

    /* =========================================================
       EXPORT LINKS
    ========================================================= */

    function updateExports() {
        const baseline =
            $("#baselineYear").value;

        const current =
            $("#currentYear").value;

        const reportButton =
            $("#exportReportBtn");

        const geojsonButton =
            $("#exportGeojsonBtn");

        if (
            !reportButton ||
            !geojsonButton
        ) {
            return;
        }

        reportButton.href =
            `${API}/api/export/report?baseline_year=${encodeURIComponent(
                baseline
            )}&current_year=${encodeURIComponent(
                current
            )}`;

        geojsonButton.href =
            `${API}/api/export/geojson?baseline_year=${encodeURIComponent(
                baseline
            )}&current_year=${encodeURIComponent(
                current
            )}`;

        reportButton.classList.remove(
            "disabled"
        );

        geojsonButton.classList.remove(
            "disabled"
        );
    }

    /* =========================================================
       RENDER COMPLETE ANALYSIS
    ========================================================= */

    function renderAnalysis(metadata) {
        state.activeAnalysis = metadata;

        $("#summaryPeriod").textContent =
            `${$("#baselineYear").value} → ${$("#currentYear").value}`;

        renderStats(metadata);
        renderSceneInfo(metadata);
        updateMap(metadata);
        updateExports();
    }

    /* =========================================================
       RUN ANALYSIS
    ========================================================= */

    async function runAnalysis() {
        const baseline = Number(
            $("#baselineYear").value
        );

        const current = Number(
            $("#currentYear").value
        );

        if (
            !Number.isInteger(baseline) ||
            !Number.isInteger(current) ||
            baseline >= current
        ) {
            showToast(
                "Choose an earlier baseline year and a later current year.",
                "error"
            );

            return;
        }

        const button =
            $("#runAnalysisBtn");

        if (!button) {
            return;
        }

        button.disabled = true;

        button.innerHTML = `
            <i class="fa-solid fa-spinner fa-spin"></i>
            Running...
        `;

        setAnalysisStatus(
            "Generating analysis...",
            true
        );

        try {
            const response =
                await fetch(
                    `${API}/api/run-analysis`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            baseline_year:
                                baseline,
                            current_year:
                                current
                        })
                    }
                );

            const data =
                await response.json();

            if (
                !response.ok ||
                data.success === false
            ) {
                throw new Error(
                    data.error ||
                        data.message ||
                        "Analysis request failed."
                );
            }

            const metadata =
                data.metadata ||
                data.analysis ||
                data;

            renderAnalysis(
                metadata
            );

            setAnalysisStatus(
                "Analysis complete"
            );

            showToast(
                `${baseline} → ${current} analysis is ready.`
            );
        } catch (error) {
            console.error(error);

            setAnalysisStatus(
                "Analysis failed"
            );

            showToast(
                error.message ||
                    "Unable to run analysis.",
                "error"
            );
        } finally {
            button.disabled = false;

            button.innerHTML = `
                <i class="fa-solid fa-wand-magic-sparkles"></i>
                Run Analysis
            `;
        }
    }

    /* =========================================================
       INITIAL ANALYSIS
    ========================================================= */

    async function loadInitial() {
        try {
            const response =
                await fetch(
                    `${API}/api/analysis`
                );

            if (response.ok) {
                const data =
                    await response.json();

                const metadata =
                    data.analysis ||
                    data.metadata ||
                    data;

                renderStats(
                    metadata
                );

                renderSceneInfo(
                    metadata
                );
            }
        } catch (error) {
            console.debug(
                "Initial analysis metadata unavailable",
                error
            );
        }

        try {
            const response =
                await fetch(
                    `${API}/api/deforestation`
                );

            if (
                response.ok &&
                state.map
            ) {
                const data =
                    await response.json();

                if (
                    Array.isArray(
                        data?.features
                    )
                ) {
                    const layer =
                        L.geoJSON(
                            data,
                            {
                                style: {
                                    color: "#f36d6d",
                                    weight: 1.2,
                                    fillColor: "#f36d6d",
                                    fillOpacity: 0.45
                                }
                            }
                        );

                    state.layers.loss =
                        layer;

                    if (
                        $("#layerLoss")
                            ?.checked
                    ) {
                        layer.addTo(
                            state.map
                        );
                    }
                }
            }
        } catch (error) {
            console.debug(
                "Static GeoJSON unavailable",
                error
            );
        }
    }

    /* =========================================================
       HEALTH CHECK
    ========================================================= */

    async function checkHealth() {
        try {
            const response =
                await fetch(
                    `${API}/api/health`
                );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error();
            }

            $("#healthText").textContent =
                data.status
                    ? `Monitoring service ${data.status}`
                    : "Monitoring service online";
        } catch {
            $("#healthText").textContent =
                "Monitoring service needs attention";
        }
    }

    /* =========================================================
       LOCATION SEARCH
    ========================================================= */

    async function searchLocation(
        query
    ) {
        const value =
            query.trim();

        if (!value) {
            return;
        }

        $("#searchResults").classList.remove(
            "visible"
        );

        setAnalysisStatus(
            "Searching map...",
            true
        );

        try {
            const response =
                await fetch(
                    `${API}/api/geocode?q=${encodeURIComponent(
                        value
                    )}`
                );

            if (!response.ok) {
                throw new Error(
                    "Location search failed."
                );
            }

            const raw =
                await response.json();

            state.searchResults = (
                Array.isArray(raw)
                    ? raw
                    : (
                          raw.results ||
                          raw.data ||
                          []
                      )
            ).slice(0, 6);

            if (
                !state.searchResults.length
            ) {
                showToast(
                    "No matching location was found.",
                    "info"
                );

                setAnalysisStatus(
                    "Ready"
                );

                return;
            }

            const resultsBox =
                $("#searchResults");

            resultsBox.innerHTML =
                state.searchResults
                    .map(
                        (
                            item,
                            index
                        ) => `
                            <button
                                class="search-result-item"
                                data-search-index="${index}"
                                type="button"
                            >
                                <strong>
                                    ${escapeHTML(
                                        item.display_name ||
                                            item.name ||
                                            item.display ||
                                            "Unknown location"
                                    )}
                                </strong>

                                <small>
                                    ${escapeHTML(
                                        item.type ||
                                            item.category ||
                                            item.address
                                                ?.state ||
                                            ""
                                    )}
                                </small>
                            </button>
                        `
                    )
                    .join("");

            resultsBox.classList.add(
                "visible"
            );

            $$(
                ".search-result-item",
                resultsBox
            ).forEach(button => {
                button.addEventListener(
                    "click",
                    () => {
                        const item =
                            state.searchResults[
                                Number(
                                    button.dataset.searchIndex
                                )
                            ];

                        selectSearchResult(
                            item
                        );
                    }
                );
            });

            setAnalysisStatus(
                "Choose a map result"
            );
        } catch (error) {
            console.error(
                error
            );

            setAnalysisStatus(
                "Search failed"
            );

            showToast(
                error.message ||
                    "Unable to search this location.",
                "error"
            );
        }
    }

    function selectSearchResult(
        item
    ) {
        const latitude = Number(
            item.lat ??
                item.latitude ??
                item.location?.lat
        );

        const longitude = Number(
            item.lon ??
                item.lng ??
                item.longitude ??
                item.location?.lon
        );

        const label =
            item.display_name ||
            item.name ||
            "Selected location";

        if (
            !Number.isFinite(
                latitude
            ) ||
            !Number.isFinite(
                longitude
            ) ||
            !state.map
        ) {
            showToast(
                "This search result does not contain map coordinates.",
                "error"
            );

            return;
        }

        if (state.marker) {
            state.map.removeLayer(
                state.marker
            );
        }

        state.marker =
            L.marker([
                latitude,
                longitude
            ])
                .addTo(state.map)
                .bindPopup(
                    `<strong>${escapeHTML(
                        label
                    )}</strong>`
                )
                .openPopup();

        state.map.setView(
            [
                latitude,
                longitude
            ],
            12
        );

        $("#locationSearch").value =
            label;

        $("#mapLocationTitle").textContent =
            label;

        $("#searchResults").classList.remove(
            "visible"
        );

        setAnalysisStatus(
            "Map location selected"
        );
    }

    function setupLocationSearch() {
        $("#searchLocationBtn")?.addEventListener(
            "click",
            () => {
                searchLocation(
                    $("#locationSearch").value
                );
            }
        );

        $("#locationSearch")?.addEventListener(
            "keydown",
            event => {
                if (event.key === "Enter") {
                    searchLocation(
                        event.target.value
                    );
                }
            }
        );

        $$(".location-chip").forEach(
            button => {
                button.addEventListener(
                    "click",
                    () => {
                        const query =
                            button.dataset
                                .query || "";

                        $("#locationSearch").value =
                            query;

                        searchLocation(
                            query
                        );
                    }
                );
            }
        );

        document.addEventListener(
            "click",
            event => {
                const container =
                    $(".control-grow");

                if (
                    container &&
                    !container.contains(
                        event.target
                    )
                ) {
                    $(
                        "#searchResults"
                    )?.classList.remove(
                        "visible"
                    );
                }
            }
        );
    }

    /* =========================================================
       ANALYSIS BUTTONS
    ========================================================= */

    function setupAnalysisButtons() {
        $("#runAnalysisBtn")?.addEventListener(
            "click",
            runAnalysis
        );

        $("#heroAnalyzeBtn")?.addEventListener(
            "click",
            () => {
                $("#analysis")?.scrollIntoView(
                    {
                        behavior:
                            "smooth"
                    }
                );
            }
        );

        $("#headerStartBtn")?.addEventListener(
            "click",
            () => {
                $("#analysis")?.scrollIntoView(
                    {
                        behavior:
                            "smooth"
                    }
                );
            }
        );

        $("#resetMapBtn")?.addEventListener(
            "click",
            () => {
                if (!state.map) {
                    return;
                }

                if (
                    state.mapInitialBounds
                ) {
                    state.map.fitBounds(
                        state.mapInitialBounds,
                        {
                            padding: [18, 18]
                        }
                    );
                } else {
                    state.map.setView(
                        [12.167, 75.49],
                        9
                    );
                }

                if (state.marker) {
                    state.map.removeLayer(
                        state.marker
                    );

                    state.marker = null;
                }
            }
        );
    }

    /* =========================================================
       REPORTS / COMPLAINT
    ========================================================= */

    function getReports() {
        try {
            const reports =
                JSON.parse(
                    localStorage.getItem(
                        STORAGE.reports
                    ) || "[]"
                );

            return Array.isArray(
                reports
            )
                ? reports
                : [];
        } catch {
            return [];
        }
    }

    function saveReports(
        reports
    ) {
        localStorage.setItem(
            STORAGE.reports,
            JSON.stringify(
                reports
            )
        );
    }

    function renderReportHistory() {
        const box =
            $("#reportHistory");

        const reports =
            getReports();

        if (!box) {
            return;
        }

        $("#reportCountChip").textContent =
            String(reports.length);

        if (!reports.length) {
            box.innerHTML = `
                <div class="empty-state compact">
                    <span>
                        <i class="fa-regular fa-file-lines"></i>
                    </span>
                    <p>
                        No reports submitted from this browser yet.
                    </p>
                </div>
            `;

            return;
        }

        box.innerHTML =
            reports
                .slice(0, 6)
                .map(
                    report => `
                        <article class="history-item">
                            <div class="history-item-top">
                                <strong>
                                    ${escapeHTML(
                                        report.id
                                    )}
                                </strong>

                                <span>
                                    ${escapeHTML(
                                        report.status
                                    )}
                                </span>
                            </div>

                            <div class="history-item-meta">
                                <span>
                                    ${escapeHTML(
                                        report.type
                                    )}
                                </span>

                                <span>
                                    ${escapeHTML(
                                        report.createdAtLabel
                                    )}
                                </span>
                            </div>
                        </article>
                    `
                )
                .join("");
    }

    function setupReport() {
        const form =
            $("#reportForm");

        if (!form) {
            return;
        }

        $("#reportDate").valueAsDate =
            new Date();

        $("#useAnalysisLocationBtn")?.addEventListener(
            "click",
            () => {
                const location =
                    $(
                        "#mapLocationTitle"
                    )
                        ?.textContent
                        ?.trim();

                if (
                    location
                ) {
                    $("#reportLocation").value =
                        location;

                    showToast(
                        "Map location copied to the report."
                    );
                }
            }
        );

        $("#communityReportBtn")?.addEventListener(
            "click",
            () => {
                $("#report")?.scrollIntoView(
                    {
                        behavior:
                            "smooth"
                    }
                );

                setTimeout(
                    () => {
                        $("#reportType")
                            ?.focus();
                    },
                    500
                );
            }
        );

        form.addEventListener(
            "submit",
            event => {
                event.preventDefault();

                const reports =
                    getReports();

                const report = {
                    id: `FM-${new Date().getFullYear()}-${String(
                        reports.length + 1
                    ).padStart(
                        4,
                        "0"
                    )}`,

                    name:
                        $("#reportName")
                            .value
                            .trim(),

                    email:
                        $("#reportEmail")
                            .value
                            .trim(),

                    type:
                        $("#reportType")
                            .value,

                    date:
                        $("#reportDate")
                            .value,

                    location:
                        $(
                            "#reportLocation"
                        )
                            .value
                            .trim() ||
                        "Location not specified",

                    message:
                        $(
                            "#reportMessage"
                        )
                            .value
                            .trim(),

                    satelliteEvidence:
                        $(
                            "#reportSatelliteEvidence"
                        )
                            .checked,

                    communityShare:
                        $(
                            "#reportCommunityShare"
                        )
                            .checked,

                    status:
                        "Submitted",

                    createdAtLabel:
                        new Date().toLocaleString(
                            "en-IN",
                            {
                                day: "2-digit",
                                month: "short",
                                year: "numeric"
                            }
                        )
                };

                reports.unshift(
                    report
                );

                saveReports(
                    reports
                );

                renderReportHistory();

                form.reset();

                $("#reportDate").valueAsDate =
                    new Date();

                showToast(
                    `Report ${report.id} submitted locally.`
                );

                if (
                    report.communityShare
                ) {
                    showToast(
                        "Report saved. Community sharing is ready for the demo.",
                        "info"
                    );
                }
            }
        );
    }

    /* =========================================================
       COMMUNITIES
    ========================================================= */

    function getCommunities() {
        try {
            const saved =
                JSON.parse(
                    localStorage.getItem(
                        STORAGE.communities
                    ) || "null"
                );

            if (
                Array.isArray(
                    saved
                ) &&
                saved.length
            ) {
                return saved;
            }
        } catch {
            // Ignore malformed localStorage.
        }

        const copy =
            JSON.parse(
                JSON.stringify(
                    seededCommunities
                )
            );

        localStorage.setItem(
            STORAGE.communities,
            JSON.stringify(copy)
        );

        return copy;
    }

    function saveCommunities(
        communities
    ) {
        localStorage.setItem(
            STORAGE.communities,
            JSON.stringify(
                communities
            )
        );
    }

    function iconForFocus(
        focus
    ) {
        if (
            focus === "water"
        ) {
            return "fa-water";
        }

        if (
            focus === "climate"
        ) {
            return "fa-cloud-sun";
        }

        return "fa-tree";
    }

    function renderCommunities() {
        const grid =
            $("#communityGrid");

        if (!grid) {
            return;
        }

        const query =
            $("#communitySearch")
                ?.value
                ?.trim()
                .toLowerCase() ||
            "";

        const filter =
            $(".community-filter.active")
                ?.dataset
                .filter ||
            "all";

        const communities =
            getCommunities().filter(
                community => {
                    const matchesQuery =
                        !query ||
                        [
                            community.name,
                            community.location,
                            community.focus,
                            community.description
                        ]
                            .join(
                                " "
                            )
                            .toLowerCase()
                            .includes(
                                query
                            );

                    const matchesFilter =
                        filter ===
                            "all" ||
                        community.focus ===
                            filter;

                    return (
                        matchesQuery &&
                        matchesFilter
                    );
                }
            );

        if (!communities.length) {
            grid.innerHTML = `
                <div
                    class="empty-state"
                    style="grid-column:1/-1"
                >
                    <span>
                        <i class="fa-solid fa-users-slash"></i>
                    </span>

                    <p>
                        No communities match this search.
                    </p>
                </div>
            `;

            return;
        }

        grid.innerHTML =
            communities
                .map(
                    community => `
                        <article class="community-card">

                            <div class="community-card-top">

                                <span class="community-symbol">
                                    <i class="fa-solid ${iconForFocus(
                                        community.focus
                                    )}"></i>
                                </span>

                                <span class="focus-tag">
                                    ${escapeHTML(
                                        community.focus
                                    )}
                                </span>

                            </div>

                            <h3>
                                ${escapeHTML(
                                    community.name
                                )}
                            </h3>

                            <p>
                                ${escapeHTML(
                                    community.description
                                )}
                            </p>

                            <div class="community-meta">

                                <span>
                                    <i class="fa-solid fa-location-dot"></i>
                                    ${escapeHTML(
                                        community.location ||
                                            "Regional"
                                    )}
                                </span>

                                <span>
                                    <i class="fa-solid fa-user-group"></i>
                                    ${formatNumber(
                                        community.members
                                    )}
                                </span>

                                <span>
                                    <i class="fa-solid fa-message"></i>
                                    ${formatNumber(
                                        community.posts
                                    )}
                                </span>

                            </div>

                            <div class="community-card-footer">

                                <span class="member-pill">

                                    <i class="fa-solid ${
                                        community.joined
                                            ? "fa-check"
                                            : "fa-user-plus"
                                    }"></i>

                                    ${
                                        community.joined
                                            ? "Joined"
                                            : "Open to join"
                                    }

                                </span>

                                <button
                                    class="btn ${
                                        community.joined
                                            ? "btn-outline"
                                            : "btn-primary"
                                    } btn-small community-open-btn"
                                    data-community-id="${escapeHTML(
                                        community.id
                                    )}"
                                    type="button"
                                >
                                    ${
                                        community.joined
                                            ? "Open"
                                            : "Join"
                                    }
                                </button>

                            </div>

                        </article>
                    `
                )
                .join("");

        $$(
            ".community-open-btn",
            grid
        ).forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    openCommunity(
                        button.dataset
                            .communityId
                    );
                }
            );
        });
    }

    function openCommunity(
        id
    ) {
        const communities =
            getCommunities();

        const community =
            communities.find(
                item =>
                    item.id === id
            );

        if (!community) {
            return;
        }

        if (!community.joined) {
            community.joined =
                true;

            community.members +=
                1;

            saveCommunities(
                communities
            );

            renderCommunities();

            showToast(
                `Joined ${community.name}.`
            );
        }

        $("#communityDetailContent").innerHTML = `
            <div class="modal-community-hero">

                <span class="community-symbol">
                    <i class="fa-solid ${iconForFocus(
                        community.focus
                    )}"></i>
                </span>

                <div>
                    <h3>
                        ${escapeHTML(
                            community.name
                        )}
                    </h3>

                    <p>
                        <i class="fa-solid fa-location-dot"></i>
                        ${escapeHTML(
                            community.location ||
                                "Regional"
                        )}
                        ·
                        ${formatNumber(
                            community.members
                        )}
                        members
                    </p>
                </div>

                <span class="member-pill">
                    <i class="fa-solid fa-check"></i>
                    Joined
                </span>

            </div>

            <div class="community-detail-grid">

                <div class="community-detail-box">

                    <h4>
                        About this community
                    </h4>

                    <p>
                        ${escapeHTML(
                            community.description
                        )}
                    </p>

                </div>

                <div class="community-detail-box">

                    <h4>
                        Community signals
                    </h4>

                    <p>
                        ${formatNumber(
                            community.posts
                        )}
                        discussion posts ·
                        ${escapeHTML(
                            community.focus
                        )}
                        focus
                    </p>

                </div>

            </div>

            <div class="share-post-box">

                <strong>
                    Share your latest Forest Monitor analysis
                </strong>

                <p id="shareCommunityText">
                    No analysis selected yet.
                    Run an analysis first, then use
                    “Share to Community”.
                </p>

                <button
                    class="btn btn-primary btn-small"
                    id="shareNowBtn"
                    type="button"
                >
                    <i class="fa-solid fa-share-nodes"></i>
                    Share latest analysis
                </button>

            </div>
        `;

        $("#shareNowBtn")?.addEventListener(
            "click",
            () => {
                if (
                    !state.activeAnalysis
                ) {
                    showToast(
                        "Run a forest analysis before sharing it.",
                        "info"
                    );

                    return;
                }

                community.posts +=
                    1;

                saveCommunities(
                    communities
                );

                $("#shareCommunityText").textContent =
                    `${$("#baselineYear").value} → ${$("#currentYear").value} analysis shared as a community post.`;

                showToast(
                    `Analysis shared to ${community.name}.`
                );
            }
        );

        openModal(
            "communityDetailModal"
        );
    }

    function setupCommunity() {
        renderCommunities();

        $("#communitySearch")?.addEventListener(
            "input",
            renderCommunities
        );

        $$(".community-filter").forEach(
            button => {
                button.addEventListener(
                    "click",
                    () => {
                        $$(".community-filter").forEach(
                            item =>
                                item.classList.remove(
                                    "active"
                                )
                        );

                        button.classList.add(
                            "active"
                        );

                        renderCommunities();
                    }
                );
            }
        );

        $("#createCommunityBtn")?.addEventListener(
            "click",
            () => {
                openModal(
                    "communityModal"
                );
            }
        );

        $("#communityForm")?.addEventListener(
            "submit",
            event => {
                event.preventDefault();

                const communities =
                    getCommunities();

                const name =
                    $("#communityName")
                        .value
                        .trim();

                const location =
                    $("#communityLocation")
                        .value
                        .trim() ||
                    "Regional";

                const focus =
                    $("#communityFocus")
                        .value;

                const description =
                    $(
                        "#communityDescription"
                    )
                        .value
                        .trim();

                const newCommunity = {
                    id: `${name
                        .toLowerCase()
                        .replace(
                            /[^a-z0-9]+/g,
                            "-"
                        )}-${Date.now()}`,

                    name,
                    location,
                    focus,
                    description,
                    members: 1,
                    posts: 0,
                    joined: true
                };

                communities.unshift(
                    newCommunity
                );

                saveCommunities(
                    communities
                );

                renderCommunities();

                closeModal(
                    "communityModal"
                );

                event.target.reset();

                showToast(
                    `${name} created successfully.`
                );
            }
        );

        $("#shareAnalysisBtn")?.addEventListener(
            "click",
            () => {
                if (
                    !state.activeAnalysis
                ) {
                    showToast(
                        "Run an analysis before sharing it.",
                        "info"
                    );

                    return;
                }

                const first =
                    getCommunities()[0];

                if (first) {
                    openCommunity(
                        first.id
                    );
                }
            }
        );
    }

    /* =========================================================
       NEWSLETTER
    ========================================================= */

    function setupNewsletter() {
        $("#newsletterForm")?.addEventListener(
            "submit",
            event => {
                event.preventDefault();

                const email =
                    $("#newsletterEmail")
                        .value
                        .trim();

                localStorage.setItem(
                    STORAGE.newsletter,
                    email
                );

                event.target.reset();

                showToast(
                    "Subscription saved for this demo."
                );
            }
        );
    }

    /* =========================================================
       APP BOOT
    ========================================================= */

    function boot() {
        setupTheme();
        setupNavigation();
        setupScrollControls();
        setupModalHandlers();

        populateYears();

        initializeMap();
        bindLayerToggles();

        setupLocationSearch();
        setupAnalysisButtons();

        setupReport();
        setupCommunity();
        setupNewsletter();

        renderReportHistory();

        checkHealth();
        loadInitial();

        setTimeout(() => {
            state.map?.invalidateSize();
        }, 250);
    }

    document.addEventListener(
        "DOMContentLoaded",
        boot
    );
})();