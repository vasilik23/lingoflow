/* Keep focused page controls above the fixed mobile navigation. */
(function () {
  "use strict";
  const navigation = document.querySelector('.app-nav');
  const main = document.getElementById('main-content');
  if (!navigation || !main) return;

  function reveal(target) {
    // Focus can change again before the browser's native focus scroll finishes.
    if (target !== document.activeElement || !main.contains(target) || target.closest('dialog')) return;
    const nav = navigation.getBoundingClientRect();
    // Desktop navigation is a sidebar, not an obstruction at the bottom.
    if (getComputedStyle(navigation).position !== 'fixed' || nav.width < window.innerWidth * 0.75) return;
    const rect = target.getBoundingClientRect();
    const bottom = Math.min(nav.top, window.innerHeight) - 12;
    if (rect.height > 0 && rect.bottom > bottom) {
      // Do not change focus, submit forms, or animate a keyboard correction.
      window.scrollBy({top: rect.bottom - bottom, behavior: 'instant'});
    }
  }

  document.addEventListener('focusin', function (event) {
    const target = event.target;
    if (!main.contains(target)) return;
    requestAnimationFrame(function () { reveal(target); });
  });
}());
