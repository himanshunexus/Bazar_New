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

  document.addEventListener("DOMContentLoaded", initializeCountdown);
})();
