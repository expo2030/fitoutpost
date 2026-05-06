/**
 * FitOut Post — Cookie Consent Banner
 * GDPR-compliant, pure JS, no dependencies.
 * Stores choice in localStorage: fop_cookie_consent = "accepted" | "necessary"
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'fop_cookie_consent';
  var BANNER_ID   = 'fop-cookie-banner';

  // Already decided? Do nothing.
  if (localStorage.getItem(STORAGE_KEY)) return;

  // ── Styles ─────────────────────────────────────────────────────────────────
  var css = [
    '#fop-cookie-banner {',
    '  position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;',
    '  background: #1a1a1a; color: #D4C4BA;',
    '  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;',
    '  font-size: 13px; line-height: 1.5;',
    '  border-top: 2px solid #990033;',
    '  padding: 0;',
    '  box-shadow: 0 -4px 24px rgba(0,0,0,.4);',
    '  transform: translateY(100%);',
    '  transition: transform .35s cubic-bezier(.4,0,.2,1);',
    '}',
    '#fop-cookie-banner.fop-cb-visible { transform: translateY(0); }',
    '#fop-cb-inner {',
    '  max-width: 1320px; margin: 0 auto;',
    '  padding: 18px 24px;',
    '  display: flex; align-items: center; gap: 32px; flex-wrap: wrap;',
    '}',
    '#fop-cb-text { flex: 1; min-width: 240px; }',
    '#fop-cb-text strong { color: #fff; font-weight: 600; }',
    '#fop-cb-text a { color: #D4C4BA; text-decoration: underline; }',
    '#fop-cb-text a:hover { color: #fff; }',
    '#fop-cb-buttons { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }',
    '.fop-cb-btn {',
    '  font-family: inherit; font-size: 12.5px; font-weight: 600;',
    '  padding: 9px 20px; border: none; cursor: pointer;',
    '  letter-spacing: 0.2px; transition: background .15s, color .15s;',
    '  white-space: nowrap;',
    '}',
    '.fop-cb-btn-accept { background: #990033; color: #fff; }',
    '.fop-cb-btn-accept:hover { background: #CC0044; }',
    '.fop-cb-btn-necessary { background: transparent; color: #9A8A80; border: 1px solid #3a3a3a; }',
    '.fop-cb-btn-necessary:hover { color: #D4C4BA; border-color: #666; }',
    '@media (max-width: 640px) {',
    '  #fop-cb-inner { flex-direction: column; align-items: flex-start; gap: 16px; }',
    '  #fop-cb-buttons { width: 100%; }',
    '  .fop-cb-btn { flex: 1; text-align: center; }',
    '}'
  ].join('\n');

  var styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── Banner HTML ───────────────────────────────────────────────────────────
  var banner = document.createElement('div');
  banner.id = BANNER_ID;
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Cookie consent');
  banner.innerHTML = [
    '<div id="fop-cb-inner">',
    '  <div id="fop-cb-text">',
    '    <strong>We use cookies</strong> to deliver FitOut Post intelligence and improve your experience.',
    '    Analytics cookies help us understand how the platform is used.',
    '    <a href="legal.html">Cookie Policy</a> &nbsp;·&nbsp; <a href="legal.html">Privacy Policy</a>',
    '  </div>',
    '  <div id="fop-cb-buttons">',
    '    <button class="fop-cb-btn fop-cb-btn-necessary" id="fop-cb-necessary">Necessary only</button>',
    '    <button class="fop-cb-btn fop-cb-btn-accept"    id="fop-cb-accept">Accept all cookies</button>',
    '  </div>',
    '</div>'
  ].join('');

  document.body.appendChild(banner);

  // Show with slight delay so the CSS transition fires
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      banner.classList.add('fop-cb-visible');
    });
  });

  // ── Handlers ─────────────────────────────────────────────────────────────
  function dismiss(choice) {
    localStorage.setItem(STORAGE_KEY, choice);
    banner.style.transition = 'transform .25s cubic-bezier(.4,0,.2,1), opacity .25s';
    banner.style.opacity    = '0';
    banner.style.transform  = 'translateY(100%)';
    setTimeout(function () { banner.remove(); }, 280);
  }

  document.getElementById('fop-cb-accept').addEventListener('click', function () {
    dismiss('accepted');
    // Placeholder: initialise analytics here when hosting is live
    // e.g. window.dataLayer = window.dataLayer || []; gtag('consent','update',{analytics_storage:'granted'});
  });

  document.getElementById('fop-cb-necessary').addEventListener('click', function () {
    dismiss('necessary');
  });

}());
