/* Contains the logic for all theme functions that are not implemented as an explicit Sphinx 
extension. */

// Realizes zoom on images within figures
document.addEventListener("DOMContentLoaded", function() {
  mediumZoom("figure img", { background: '#1f1f1f' });
});

// Realizes the light/dark theme toggle.
document.addEventListener("DOMContentLoaded", function() {
  const body = document.body;
  const btn = document.getElementById("theme-toggle");
  const icon = document.getElementById("theme-icon");
  if (!body || !btn || !icon)
  {
    console.log("Theme toggle button or body or icon not found.");
    return;
  }

  // Map of themes to the next theme and the icon to use for that theme.
  const mxnThemeMap = {
    "light": {
      "next-theme": "dark",
      "next-icon": "bi bi-sun-fill"
    },
    "dark": {
      "next-theme": "light",
      "next-icon": "bi bi-moon-fill"
    }
  };

  // Get the theme that was already applied and apply it to body as well and set the icon.
  let startTheme = body.getAttribute("data-bs-theme") || "light";
  icon.className = mxnThemeMap[startTheme]["next-icon"];
  if (body.getAttribute("data-bs-theme") !== startTheme) {
    body.setAttribute("data-bs-theme", startTheme);
  }

  // Event listener for the button to toggle the theme and icon.
  btn.addEventListener("click", function() {
    const currentTheme = body.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
    body.setAttribute("data-bs-theme", mxnThemeMap[currentTheme]["next-theme"]);
    icon.className = mxnThemeMap[currentTheme]["next-icon"];
    localStorage.setItem("bs-theme", mxnThemeMap[currentTheme]["next-theme"]); // persist the choice

  });
});

// Sets the theme of the site based on the saved preference or the system preference.
//
// Called from the body while the page is being built to avoid flickering.
function SetMxnSiteTheme () {
  let theme = localStorage.getItem("bs-theme");
  if (!theme) {
      theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.body.setAttribute("data-bs-theme", theme);
}

// Banner data.
mxn_banner_data = [
  {
    uri: "_static/media/banners/banner_nacho_riesco_panther.jpg",
    artist: "Nacho Riesco",
    position: "0% 22.5%",
  },
  {
    uri: "_static/media/banners/banner_joseph_drust_spaceship.jpg",
    artist: "Joseph Drust",
    position: "0% 70%",
  },
  {
    uri: "_static/media/banners/banner_vahid_ahmadi_owl_woman.jpg",
    artist: "Vahid Ahmadi",
    position: "0% 30%",
  },
  {
    uri: "_static/media/banners/banner_ali_jalali_skull_woman.jpg",
    artist: "Ali Jalali",
    position: "0% 40%",
  },
  {
    uri: "_static/media/banners/banner_borhat_flamenco.jpg",
    artist: "Borhat",
    position: "0% 40%",
  },
  {
    uri: "_static/media/banners/banner_marvel_studios_groot.png",
    artist: "Marvel Studios",
    position: "0% 20%",
  },
  // {
  //   uri: "_static/media/banners/banner_zhelong_zhu_owl_dragon.png",
  //   artist: "Zhelong Zhu",
  //   position: "0% 10%",
  // },
  {
    uri: "_static/media/banners/banner_gengyx_zbrushcentral_crow.png",
    artist: "GengYX / ZBrushCentral",
    position: "0% 30%",
  },
  {
    uri: "_static/media/banners/banner_joseph_drust_tool.jpg",
    artist: "Joseph Drust",
    position: "0% 50%",
  },
];

// Randomly sets the banner based on a hash of the current time. 
//
// Also called while the site is being built to set the banner immediately and avoid flashing.
function SetMxnSiteBanner () {
  const banner = document.getElementById("mxn-banner-image");
  if (!banner) return; 
  
  // Get the hours passed since epoch (1970-01-01), the banner changes every minute.
  const t = new Date().getTime() / 1000 / 60; // ms / s
  var i = Math.floor(t) % mxn_banner_data.length;
  // i = Math.floor(Math.random() * mxn_banner_data.length);
  const data = mxn_banner_data[i];

  banner.src = data.uri;
  banner.style.objectPosition = data.position;
  const credit = document.getElementById("mxn-banner-credit");
  if (credit) {
    credit.textContent = `© ${data.artist}`;
  }
}