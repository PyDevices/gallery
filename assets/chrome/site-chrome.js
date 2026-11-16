/*
 * PyDevices — shared site header, footer & left-side navigation drawer
 *
 * Injects identical chrome into pages that provide mount points:
 *   <div id="pydevices-site-header"></div>
 *   ...
 *   <div id="pydevices-site-footer"></div>
 *   <script src="https://omnipython.org/assets/chrome/site-chrome.js"></script>
 *
 * That one script is the whole of it -- the theme toggle is built in below.
 */
(function () {
  'use strict';

  var chromeScript = document.querySelector('script[src*="site-chrome.js"]');
  var ROOT = '';
  if (chromeScript && chromeScript.src.startsWith('http')) {
    try {
      var scriptUrl = new URL(chromeScript.src);
      if (scriptUrl.origin !== window.location.origin) {
        ROOT = scriptUrl.origin;
      }
    } catch (e) {}
  }
  var LOGO = (ROOT || '') + '/assets/img/logo.svg';
  /* Three pads a side: the drawing for slots under about 32 px. */
  var LOGO_SMALL = (ROOT || '') + '/assets/img/logo-small.svg';

  var HEADER =
    '<header class="site-header">' +
    '<div class="wrap">' +
    '<a class="brand" href="' +
    ROOT +
    '/">' +
    '<span class="logo"><img src="' +
    LOGO +
    '" alt="" width="36" height="36"></span>' +
    "PyDevices" +
    "</a>" +
    '<nav class="nav">' +
    '<a href="https://github.com/PyDevices">GitHub</a>' +
    '<a href="' +
    ROOT +
    '/omnipython/">Core Stack</a>' +
    '<a href="' +
    ROOT +
    '/omnipython-builds/">Firmware</a>' +
    '<a href="https://workbench.pydevices.com/">Workbench</a>' +
    '<a href="https://gallery.omnipython.org/" class="nav-gallery-link">Gallery</a>' +
    "</nav>" +
    '<button type="button" class="theme-toggle" id="theme-toggle" aria-label="Toggle color theme" title="Toggle color theme">' +
    '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v1.5M12 20v1.5M5.3 5.3l1.1 1.1M17.6 17.6l1.1 1.1M2.5 12H4M20 12h1.5M5.3 18.7l1.1-1.1M17.6 6.4l1.1-1.1"/></svg>' +
    '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 13.2A8.5 8.5 0 1 1 10.8 3.5a6.7 6.7 0 0 0 9.7 9.7z"/></svg>' +
    "</button>" +
    "</div>" +
    "</header>";

  var FOOTER =
    '<footer class="site-footer">' +
    '<div class="wrap">' +
    '<span class="footer-brand"><img src="' +
    LOGO_SMALL +
    '" alt="" width="26" height="26">&copy; 2026 PyDevices &middot; MIT License</span>' +
    '<span><a href="https://github.com/PyDevices">github.com/PyDevices</a></span>' +
    "</div>" +
    "</footer>";

  /* Tier colours live in assets/css/site.css. The hexes below are only the
   * var() fallbacks for a page that failed to load the shared stylesheet, so
   * they must stay equal to that file's --tier-N-* values -- never a second,
   * different palette. A palette change is a site.css token-block edit plus a
   * mechanical refresh of these five fallbacks. */
  var ECOSYSTEM_DATA = [
    {
      tier: 0,
      name: "Organization Portal",
      color: "var(--tier-1-amber, #f59e0b)",
      repos: [
        {
          id: "root",
          name: "PyDevices",
          path: "/",
          url: ROOT + "/",
          tag: "HOME",
          desc: "Universal board contract & Python graphics umbrella",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.7 3.6q1.3-.7 2.6 0l6.6 3.5q1.6.9 0 1.8l-6.6 3.5q-1.3.7-2.6 0L4.1 8.9q-1.6-.9 0-1.8z"/><path d="M3.6 12.6l7.2 3.8q1.2.6 2.4 0l7.2-3.8"/><path d="M3.6 16.6l7.2 3.8q1.2.6 2.4 0l7.2-3.8" stroke="var(--accent, currentColor)"/></svg>'
        }
      ]
    },
    {
      tier: 1,
      name: "Core Platform & HAL",
      color: "var(--tier-1-amber, #f59e0b)",
      repos: [
        {
          id: "omnipython",
          name: "omnipython",
          path: "/omnipython/",
          url: ROOT + "/omnipython/",
          tag: "Core HAL",
          desc: "Unified display HAL & device driver abstraction",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="3.5" width="19" height="13" rx="4"/><path d="M12 16.5v3.5M8 20.5h8"/><circle cx="12" cy="10" r="2.8"/><circle cx="12.6" cy="9.6" r="1.1" fill="var(--accent, currentColor)" stroke="none"/></svg>'
        },
        {
          id: "audiodsp",
          name: "audiodsp",
          path: "/audiodsp/",
          url: ROOT + "/audiodsp/",
          tag: "C Audio",
          desc: "CircuitPython audio stack as MicroPython usermods",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10.5v3M8 7.5v9M16 7.5v9M20 10.5v3"/><path d="M12 4v16" stroke="var(--accent, currentColor)"/></svg>'
        },
        {
          id: "audioinstruments",
          name: "audioinstruments",
          path: "/audioinstruments/",
          url: ROOT + "/audioinstruments/",
          tag: "Instruments",
          desc: "33 playable instruments on audiodsp",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="3.5"/><path d="M9 12.5V19M15 12.5V19"/><path d="M9 5.5v6M15 5.5v6" stroke="var(--accent, currentColor)" stroke-width="3"/></svg>'
        },
        {
          id: "audioeffects",
          name: "audioeffects",
          path: "/audioeffects/",
          url: ROOT + "/audioeffects/",
          tag: "Effects",
          desc: "45 studio and pedal effects on audiodsp",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4v7.5M5 16.5V20M12 4v1.5M12 10.5V20M19 4v6.5M19 15.5V20"/><g stroke="var(--accent, currentColor)"><circle cx="5" cy="14" r="2.5"/><circle cx="12" cy="8" r="2.5"/><circle cx="19" cy="13" r="2.5"/></g></svg>'
        },
        {
          id: "gallery",
          name: "gallery",
          path: "/gallery/",
          url: "https://gallery.omnipython.org/",
          tag: "Showcase",
          desc: "Multi-interpreter demos, benchmarks & PyScript runner",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3.5" width="17" height="17" rx="4.5"/><path d="M4.5 16.5c3-4.5 5.5-4.5 7.5-1.5 2-2.5 4.5-2.5 7.5.5"/><circle cx="15.2" cy="8.8" r="1.9" fill="var(--accent, currentColor)" stroke="none"/></svg>'
        }
      ]
    },
    {
      tier: 2,
      name: "Framebuffers & UI Toolkits",
      color: "var(--tier-2-emerald, #10b981)",
      repos: [
        {
          id: "pygraphics",
          name: "pygraphics",
          path: "/pygraphics/",
          url: ROOT + "/pygraphics/",
          tag: "2D FrameBuffer",
          desc: "0-dependency raster graphics, native C & pure-Python",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 3c-4.5 5-4.5 13 0 18M12 3c4.5 5 4.5 13 0 18"/><path d="M3.2 12q8.8 2.4 17.6 0" stroke="var(--accent, currentColor)"/></svg>'
        },
        {
          id: "pdwidgets",
          name: "pdwidgets",
          path: "/pdwidgets/",
          url: ROOT + "/pdwidgets/",
          tag: "UI Toolkit",
          desc: "Embedded widgets with gauges, sliders & switches",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3.5" width="17" height="17" rx="4.5"/><path d="M3.5 9.5h17M9.5 9.5v11"/><path d="M7 6.5h3.5" stroke="var(--accent, currentColor)"/></svg>'
        },
        {
          id: "palettes",
          name: "palettes",
          path: "/palettes/",
          url: ROOT + "/palettes/",
          tag: "Color Engine",
          desc: "HSV wheel, RGB cubes & RGB565 format conversion",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5c-5.3 0-9.5 4.2-9.5 9.5s4.2 9.5 9.5 9.5c1.1 0 2-.9 2-2 0-.6-.3-1-.3-1.6 0-.9.8-1.6 1.7-1.6H17c2.5 0 4.5-2 4.5-4.6 0-5-4.2-9.2-9.5-9.2z"/><circle cx="8" cy="8" r="1.4" fill="var(--accent, currentColor)" stroke="none"/><circle cx="13.5" cy="6.5" r="1.4" fill="var(--accent, currentColor)" stroke="none"/><circle cx="17.3" cy="10.3" r="1.4" fill="var(--accent, currentColor)" stroke="none"/><circle cx="6.5" cy="12.8" r="1.4" fill="var(--accent, currentColor)" stroke="none"/></svg>'
        }
      ]
    },
    {
      tier: 3,
      name: "LVGL Native Extensions",
      color: "var(--tier-3-blue, #3b82f6)",
      repos: [
        {
          id: "omnipython-lvgl",
          name: "omnipython-lvgl",
          path: "/omnipython-lvgl/",
          url: ROOT + "/omnipython-lvgl/",
          tag: "LVGL",
          desc: "LVGL v9 for MicroPython, CircuitPython and CPython",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3.5" width="7" height="7" rx="2.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="2.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="2.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="2.5" fill="var(--accent, currentColor)" stroke="var(--accent, currentColor)"/></svg>'
        }
      ]
    },
    {
      tier: 4,
      name: "App Hosts & Mobile",
      color: "var(--tier-4-purple, #8b5cf6)",
      repos: [
        {
          id: "pyscript-template",
          name: "pyscript-template",
          path: "/pyscript-template/",
          url: ROOT + "/pyscript-template/",
          tag: "PWA Template",
          desc: "Zero-config PyScript & WebAssembly app scaffold",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="3.5" width="19" height="14" rx="4"/><path d="M8 21h8M12 17.5V21M7.5 8.5h6"/><path d="M7.5 12.5h3.5" stroke="var(--accent, currentColor)"/></svg>'
        },
        {
          id: "android-template",
          name: "android-template",
          path: "/android-template/",
          url: ROOT + "/android-template/",
          tag: "Android APK",
          desc: "python-for-android / Buildozer APK template",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6.5" y="2.5" width="11" height="19" rx="3.5"/><path d="M10.8 18.3h2.4"/><path d="M10.7 8.3v4.4l3.4-2.2z" stroke="var(--accent, currentColor)"/></svg>'
        }
      ]
    },
    {
      tier: 5,
      name: "Developer Tools & Infrastructure",
      color: "var(--tier-5-steel, #06b6d4)",
      repos: [
        {
          id: "mcuctl",
          name: "mcuctl",
          path: "/mcuctl/",
          url: ROOT + "/mcuctl/",
          tag: "IDE Extension",
          desc: "Editor, CLI, and agent tools for MCU boards",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="12" rx="3.5"/><path d="M9 7.5h6M9 11h3.5"/><path d="M12 15v3c0 3.2-5 3.2-5 .2 0-2 3-2 3-.2" stroke="var(--accent, currentColor)"/></svg>'
        },
        {
          id: "omnipython-builds",
          name: "omnipython-builds",
          path: "/omnipython-builds/",
          url: ROOT + "/omnipython-builds/",
          tag: "Runtime Overlay",
          desc: "Patch queue, presets, boards & variants for MicroPython",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6.5" y="6.5" width="11" height="11" rx="3"/><path d="M9.8 3v3.5M14.2 3v3.5M9.8 17.5V21M14.2 17.5V21M3 9.8h3.5M3 14.2h3.5M17.5 9.8H21M17.5 14.2H21"/><circle cx="12" cy="12" r="1.7" fill="var(--accent, currentColor)" stroke="none"/></svg>'
        },
        {
          id: "workbench",
          name: "workbench",
          path: "/workbench/",
          url: "https://workbench.pydevices.com/",
          tag: "Browser IDE",
          desc: "MicroPython IDE with a built-in device simulator",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="4" width="19" height="16" rx="4.5"/><path d="M9.8 9.5L7.3 12l2.5 2.5M14.2 9.5l2.5 2.5-2.5 2.5" stroke="var(--accent, currentColor)"/></svg>'
        },
        {
          id: "mpvst",
          name: "mpvst",
          path: "/mpvst/",
          url: ROOT + "/mpvst/",
          tag: "VST3 Plug-in",
          desc: "The instrument and effect library inside your DAW",
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 17.5V6.3q0-.8.8-1l9-1.8q1.2-.2 1.2 1V15.5"/><g stroke="var(--accent, currentColor)"><circle cx="6.3" cy="17.5" r="2.7"/><circle cx="18.3" cy="15.5" r="2.7"/></g></svg>'
        }
      ]
    }
  ];

  function buildSidebarHtml() {
    var curPath = window.location.pathname;

    var html = '<div class="omnipython-nav-scrim" id="omnipython-nav-scrim"></div>';
    html += '<aside class="omnipython-nav-sidebar" id="omnipython-nav-sidebar" aria-label="PyDevices Ecosystem Navigation">';

    // 1. Peeking Handle (visible on screens <= 1400px when collapsed)
    html += '<div class="omnipython-nav-peeking-tab" id="omnipython-nav-peeking-tab" title="Click to browse PyDevices Ecosystem">';
    html += '  <img src="' + LOGO_SMALL + '" alt="" class="peeking-logo" width="22" height="22">';
    html += '  <span class="peeking-title">ECOSYSTEM</span>';
    html += '  <svg class="peeking-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 6l6 6-6 6" stroke-width="2.5"/></svg>';
    html += '</div>';

    // 2. Full Navigation Panel
    html += '<div class="omnipython-nav-panel">';
    html += '  <div class="omnipython-nav-header">';
    html += '    <a class="omnipython-nav-brand" href="' + ROOT + '/">';
    html += '      <img src="' + LOGO_SMALL + '" alt="PyDevices" width="28" height="28">';
    html += '      <div>';
    html += '        <div class="omnipython-nav-brand-title">PyDevices</div>';
    html += '        <div class="omnipython-nav-brand-sub">Ecosystem Navigator</div>';
    html += '      </div>';
    html += '    </a>';
    html += '    <button type="button" class="omnipython-nav-close" id="omnipython-nav-close" aria-label="Close navigation">&times;</button>';
    html += '  </div>';

    // Search Filter Input
    html += '  <div class="omnipython-nav-search-wrap">';
    html += '    <svg class="omnipython-nav-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.8" cy="10.8" r="7.3"/><path d="M16.2 16.2L20.5 20.5"/><circle cx="12" cy="9.6" r="2.2" fill="var(--accent, currentColor)" stroke="none"/></svg>';
    html += '    <input type="text" class="omnipython-nav-search" id="omnipython-nav-search" placeholder="Filter..." autocomplete="off">';
    html += '  </div>';

    // Scrollable Body with Tiers & Cards
    html += '  <div class="omnipython-nav-body" id="omnipython-nav-body">';
    for (var t = 0; t < ECOSYSTEM_DATA.length; t++) {
      var tierObj = ECOSYSTEM_DATA[t];
      html += '    <div class="omnipython-nav-tier-group" data-tier="' + tierObj.tier + '">';
      html += '      <div class="omnipython-nav-tier-head">';
      html += '        <span class="omnipython-nav-tier-pill" style="background:' + tierObj.color + '">T' + tierObj.tier + '</span>';
      html += '        <span class="omnipython-nav-tier-name">' + tierObj.name + '</span>';
      html += '      </div>';
      html += '      <div class="omnipython-nav-cards">';

      for (var r = 0; r < tierObj.repos.length; r++) {
        var repo = tierObj.repos[r];
        var isCurrent = false;

        if (repo.id === 'root') {
          isCurrent = (curPath === '/' || curPath === '/index.html' || curPath === '');
        } else if (curPath.indexOf(repo.path) !== -1 || (repo.id === 'mip' && curPath.indexOf('/mip') !== -1)) {
          isCurrent = true;
        }

        html += '        <a class="omnipython-nav-card' + (isCurrent ? ' is-active' : '') + '" href="' + repo.url + '" data-name="' + repo.name.toLowerCase() + '" data-tag="' + repo.tag.toLowerCase() + '" data-desc="' + repo.desc.toLowerCase() + '">';
        html += '          <div class="nav-card-icon" style="color:' + tierObj.color + '">' + repo.icon + '</div>';
        html += '          <div class="nav-card-content">';
        html += '            <div class="nav-card-title-row">';
        html += '              <span class="nav-card-title">' + repo.name + '</span>';
        html += '              <span class="nav-card-tag tag-tier-' + tierObj.tier + '">' + repo.tag + '</span>';
        html += '            </div>';
        html += '            <div class="nav-card-desc">' + repo.desc + '</div>';
        html += '          </div>';
        html += '        </a>';
      }

      html += '      </div>';
      html += '    </div>';
    }
    html += '  </div>';

    // Footer Links
    html += '  <div class="omnipython-nav-footer">';
    html += '    <a href="https://gallery.omnipython.org/" class="nav-foot-link">Interactive Gallery</a> &middot; ';
    html += '    <a href="https://lib.omnipython.org" class="nav-foot-link">Package Index</a> &middot; ';
    html += '    <a href="https://github.com/PyDevices" class="nav-foot-link">GitHub</a>';
    html += '  </div>';

    html += '</div>';
    html += '</aside>';

    return html;
  }

  function setupNavigationEvents() {
    var sidebar = document.getElementById('omnipython-nav-sidebar');
    var scrim = document.getElementById('omnipython-nav-scrim');
    var peekingTab = document.getElementById('omnipython-nav-peeking-tab');
    var closeBtn = document.getElementById('omnipython-nav-close');
    var searchInput = document.getElementById('omnipython-nav-search');

    if (!sidebar || !scrim) return;

    function openDrawer() {
      sidebar.classList.add('is-open');
      scrim.classList.add('is-open');
      document.body.classList.add('omnipython-drawer-open');
      var activeCard = sidebar.querySelector('.omnipython-nav-card.is-active');
      if (activeCard) {
        activeCard.focus({ preventScroll: true });
        activeCard.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      } else {
        var firstCard = sidebar.querySelector('.omnipython-nav-card');
        if (firstCard) {
          firstCard.focus({ preventScroll: true });
        }
      }
    }

    function closeDrawer() {
      sidebar.classList.remove('is-open');
      scrim.classList.remove('is-open');
      document.body.classList.remove('omnipython-drawer-open');
    }

    if (peekingTab) {
      peekingTab.addEventListener('click', function (e) {
        e.stopPropagation();
        openDrawer();
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        closeDrawer();
      });
    }

    scrim.addEventListener('click', closeDrawer);

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
        closeDrawer();
      }
    });

    // Instant Search Filter
    if (searchInput) {
      searchInput.addEventListener('input', function (e) {
        var query = e.target.value.toLowerCase().trim();
        var tierGroups = sidebar.querySelectorAll('.omnipython-nav-tier-group');

        tierGroups.forEach(function (group) {
          var cards = group.querySelectorAll('.omnipython-nav-card');
          var visibleInGroup = 0;

          cards.forEach(function (card) {
            if (!query) {
              card.style.display = '';
              visibleInGroup++;
              return;
            }
            var name = card.getAttribute('data-name') || '';
            var tag = card.getAttribute('data-tag') || '';
            var desc = card.getAttribute('data-desc') || '';

            if (name.indexOf(query) !== -1 || tag.indexOf(query) !== -1 || desc.indexOf(query) !== -1) {
              card.style.display = '';
              visibleInGroup++;
            } else {
              card.style.display = 'none';
            }
          });

          group.style.display = visibleInGroup > 0 ? '' : 'none';
        });
      });
    }
  }

  function setupThemeToggle() {
    var toggle = document.getElementById("theme-toggle");
    if (!toggle || toggle.getAttribute("data-bound")) {
      return;
    }
    toggle.setAttribute("data-bound", "true");
    toggle.addEventListener("click", function () {
      var root = document.documentElement;
      var current = root.getAttribute("data-theme") === "light" ? "light" : "dark";
      var next = current === "light" ? "dark" : "light";
      if (next === "light") {
        root.setAttribute("data-theme", "light");
      } else {
        root.removeAttribute("data-theme");
      }
      try {
        localStorage.setItem("omnipython-theme", next);
      } catch (e) {}
    });
  }

  function inject() {
    var headerMount = document.getElementById("pydevices-site-header");
    var footerMount = document.getElementById("pydevices-site-footer");
    if (headerMount) {
      headerMount.outerHTML = HEADER;
    }
    if (footerMount) {
      footerMount.outerHTML = FOOTER;
    }

    // Bind theme toggle on header
    setupThemeToggle();

    // Inject Left-Side Navigation Drawer
    if (!document.getElementById("omnipython-nav-sidebar")) {
      document.body.insertAdjacentHTML("afterbegin", buildSidebarHtml());
      setupNavigationEvents();
      document.body.classList.add("has-omnipython-nav");
    }

    var scriptEl = document.querySelector('script[src*="site-chrome.js"]');
    var base = scriptEl ? scriptEl.src.replace(/\/site-chrome\.js.*$/, '') : '/assets/chrome';

    if (document.querySelector('[data-hero-canvas]') && !document.querySelector('script[src*="hero-runtime.js"]')) {
      var heroScript = document.createElement('script');
      heroScript.src = base + '/hero-runtime.js';
      document.head.appendChild(heroScript);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", inject);
  } else {
    inject();
  }
})();
