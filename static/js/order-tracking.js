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
    const map = L.map(element).setView([22.2887, 73.3634], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    const marker = L.marker([22.2887, 73.3634]);
    const status = document.getElementById("rider-location-status");
    async function refresh() {
      try {
        const response = await fetch(element.dataset.locationUrl, {headers: {"Accept": "application/json"}});
        if (!response.ok) return;
        const {location} = await response.json();
        if (!location) { status.textContent = "Waiting for the rider to share their location."; return; }
        const point = [location.latitude, location.longitude];
        marker.setLatLng(point).addTo(map);
        map.setView(point, 15);
        status.textContent = `Rider location updated ${new Date(location.updated_at).toLocaleTimeString()}.`;
      } catch (_) { status.textContent = "Rider location is temporarily unavailable."; }
    }
    refresh();
    window.setInterval(refresh, 15000);
  }

  document.addEventListener("DOMContentLoaded", initializeCountdown);
  document.addEventListener("DOMContentLoaded", initializeRiderMap);
})();
