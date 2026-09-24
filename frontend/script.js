// Create the map centered on Karnataka
const map = L.map("map").setView([15.3173, 75.7139], 7);


// OpenStreetMap base layer
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);


// GFW integrated forest-alert layer
const gfwAlerts = L.tileLayer(
    "https://tiles.globalforestwatch.org/gfw_integrated_alerts/latest/dynamic/{z}/{x}/{y}.png",
    {
        opacity: 0.7,
        tileSize: 256
    }
).addTo(map);


// Marker for the selected region
let regionMarker = null;


// Search region
document.getElementById("searchBtn").addEventListener("click", async () => {
    const regionInput = document.getElementById("region");
    const region = regionInput.value.trim();

    if (!region) {
        alert("Please enter a region.");
        return;
    }

    try {
        const response = await fetch(
            `http://127.0.0.1:5000/api/geocode?region=${encodeURIComponent(region)}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Region not found");
        }

        const latitude = data.latitude;
        const longitude = data.longitude;

        // Move map to the selected region
        map.flyTo([latitude, longitude], 10);

        // Remove previous region marker
        if (regionMarker) {
            map.removeLayer(regionMarker);
        }

        // Add new marker
        regionMarker = L.marker([latitude, longitude])
            .addTo(map)
            .bindPopup(
                `<b>${data.display_name}</b><br>
                 Latitude: ${latitude.toFixed(4)}<br>
                 Longitude: ${longitude.toFixed(4)}`
            )
            .openPopup();

    } catch (error) {
        console.error("Region search error:", error);
        alert(error.message);
    }
});