(() => {
  const validPincode = /^\d{6}$/;

  async function geocodePincode(pincode) {
    const query = new URLSearchParams({postalcode: pincode, country: "India", format: "jsonv2", limit: "1"});
    const response = await fetch(`https://nominatim.openstreetmap.org/search?${query}`, {
      headers: {"Accept-Language": "en"},
    });
    if (!response.ok) throw new Error("Could not look up that pincode right now.");
    const matches = await response.json();
    if (!matches.length) throw new Error("We could not find that pincode. Check the number and try again.");
    return {latitude: Number(matches[0].lat), longitude: Number(matches[0].lon), source: "pincode"};
  }

  function getDeviceLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Device location is unavailable."));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        ({coords}) => resolve({latitude: coords.latitude, longitude: coords.longitude, source: "device"}),
        () => reject(new Error("Location permission was denied.")),
        {enableHighAccuracy: true, timeout: 10000, maximumAge: 60000},
      );
    });
  }

  function initialize(form) {
    const pincode = form.querySelector("#id_pincode");
    const latitude = form.querySelector("#id_latitude");
    const longitude = form.querySelector("#id_longitude");
    const status = form.querySelector("[data-location-status]");
    const useLocation = form.querySelector("[data-use-location]");
    if (!pincode || !latitude || !longitude || !status) return;

    let lastPincode = pincode.value.trim();
    let locationLookup = null;
    function setStatus(message, isError = false) {
      status.textContent = message;
      status.setAttribute("aria-live", isError ? "assertive" : "polite");
      status.classList.toggle("text-danger", isError);
    }
    function storeLocation(location) {
      if (!Number.isFinite(location.latitude) || !Number.isFinite(location.longitude)) {
        throw new Error("The location lookup returned invalid coordinates.");
      }
      latitude.value = location.latitude.toFixed(6);
      longitude.value = location.longitude.toFixed(6);
      setStatus(location.source === "device"
        ? "Your device location is ready and will be saved with this address."
        : "Using the approximate center of this pincode. You can refine it with your device location.");
    }

    async function locate({preferDevice = true} = {}) {
      const code = pincode.value.trim();
      if (!validPincode.test(code)) {
        setStatus("Enter a valid 6-digit pincode first.", true);
        pincode.focus();
        return false;
      }
      setStatus("Finding your location…");
      if (useLocation) useLocation.disabled = true;
      try {
        if (preferDevice) {
          try {
            storeLocation(await getDeviceLocation());
            return true;
          } catch (_) {
            // Use the postal-code centroid when permission is unavailable.
          }
        }
        storeLocation(await geocodePincode(code));
        return true;
      } catch (error) {
        setStatus(error.message || "Unable to determine the location for this pincode.", true);
        return false;
      } finally {
        if (useLocation) useLocation.disabled = false;
      }
    }

    pincode.addEventListener("change", () => {
      const code = pincode.value.trim();
      if (code === lastPincode) return;
      lastPincode = code;
      if (!latitude.value || !longitude.value) locationLookup = locate({preferDevice: true});
      else {
        latitude.value = "";
        longitude.value = "";
        locationLookup = locate({preferDevice: true});
      }
    });
    if (useLocation) useLocation.addEventListener("click", () => { locationLookup = locate({preferDevice: true}); });
    form.addEventListener("submit", async (event) => {
      if (!validPincode.test(pincode.value.trim()) || (latitude.value && longitude.value)) return;
      event.preventDefault();
      const submitter = event.submitter;
      const found = locationLookup ? await locationLookup : await locate({preferDevice: true});
      if (found && latitude.value && longitude.value) form.requestSubmit(submitter);
    });
    if (latitude.value && longitude.value) setStatus("Saved address location is ready.");
    else setStatus("Enter your pincode, then allow location access to save a precise delivery point.");
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".location-autofill-form").forEach(initialize);
  });
})();
