(() => {
  function initializeCountdown() {
    const tracking = document.querySelector("[data-estimated-delivery]");
    if (!tracking) return;
    const countdown = document.getElementById("delivery-countdown");
    const alert = document.getElementById("arrival-alert");
    const target = new Date(tracking.dataset.estimatedDelivery).getTime();

    function update() {
      const remaining = target - Date.now();
      if (Number.isNaN(target)) {
        countdown.textContent = "Arrival time unavailable";
        return;
      }
      if (remaining <= 0) {
        countdown.textContent = "Arriving now";
        alert.hidden = false;
        return;
      }
      const totalSeconds = Math.floor(remaining / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      countdown.textContent = `${hours}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
      alert.hidden = remaining > 10 * 60 * 1000;
    }

    update();
    window.setInterval(update, 1000);
  }

  function initializeRiderMap() {
    const element = document.getElementById("rider-map");
    if (!element || typeof L === "undefined") return;
    const shopPoint = [Number(element.dataset.shopLat), Number(element.dataset.shopLng)];
    const destinationPoint = [Number(element.dataset.destinationLat), Number(element.dataset.destinationLng)];
    if (![...shopPoint, ...destinationPoint].every(Number.isFinite)) return;
    const map = L.map(element);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    L.marker(shopPoint).addTo(map).bindPopup("Shop");
    L.marker(destinationPoint).addTo(map).bindPopup("Delivery address");
    const routePoints = [shopPoint, destinationPoint];
    L.polyline(routePoints, {color: "#c76b2b", weight: 4, opacity: 0.65, dashArray: "8 8"}).addTo(map);
    const bounds = L.latLngBounds(routePoints);
    map.fitBounds(bounds, {padding: [32, 32], maxZoom: 14});
    let marker = null;
    const status = document.getElementById("rider-location-status");
    if (!element.dataset.locationUrl || !status) return;
    async function refresh() {
      try {
        const response = await fetch(element.dataset.locationUrl, {headers: {"Accept": "application/json"}});
        if (!response.ok) return;
        const {location} = await response.json();
        if (!location) { status.textContent = "Waiting for the rider to share a recent location."; return; }
        const point = [location.latitude, location.longitude];
        if (marker) marker.setLatLng(point);
        else marker = L.marker(point).addTo(map);
        marker.bindPopup("Rider's latest location");
        bounds.extend(point);
        map.fitBounds(bounds, {padding: [32, 32], maxZoom: 15});
        status.textContent = `Rider location updated ${new Date(location.updated_at).toLocaleTimeString()}.`;
      } catch (_) { status.textContent = "Rider location is temporarily unavailable."; }
    }
    refresh();
    window.setInterval(refresh, 15000);
  }

  document.addEventListener("DOMContentLoaded", initializeCountdown);
  document.addEventListener("DOMContentLoaded", initializeRiderMap);
})();
