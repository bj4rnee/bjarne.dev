/*
 * PhotoSwipe lightbox on the collection
 * grid + a light scroll-reveal. Loaded as
 * module so it can import the vendored PhotoSwipe build.
 */
import PhotoSwipeLightbox from '/static/assets/js/photoswipe/photoswipe-lightbox.esm.js';

if (document.querySelector('#photo_grid')) {
    var lightbox = new PhotoSwipeLightbox({
        gallery: '#photo_grid',
        children: 'a.photo_link',
        pswpModule: function () {
            return import('/static/assets/js/photoswipe/photoswipe.esm.js');
        },
        bgOpacity: 0.8,
    });
    lightbox.init();
}

// pictures are AVIF-only. On a browser that can't decode AVIF, swap the
// collection grid for a warning. grid ships visible in the HTML, so crawlers and modern browsers are untouched
var grid = document.querySelector('.collection_grid');
var avifWarning = document.getElementById('avif_warning');
if (grid && avifWarning) {
    var showAvifWarning = function () {
        grid.style.display = 'none';
        avifWarning.hidden = false;
    };
    var probe = new Image();
    probe.onload = function () { if (probe.width !== 1) showAvifWarning(); };
    probe.onerror = showAvifWarning;
    probe.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADrbWV0YQAAAAAAAAAhaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAAAAAAAOcGl0bQAAAAAAAQAAAB5pbG9jAAAAAEQAAAEAAQAAAAEAAAETAAAAIQAAAChpaW5mAAAAAAABAAAAGmluZmUCAAAAAAEAAGF2MDFDb2xvcgAAAABqaXBycAAAAEtpcGNvAAAAFGlzcGUAAAAAAAAAAQAAAAEAAAAQcGl4aQAAAAADCAgIAAAADGF2MUOBAAwAAAAAE2NvbHJuY2x4AAEADQAGgAAAABdpcG1hAAAAAAAAAAEAAQQBAoMEAAAAKW1kYXQSAAoIGAAGiAhoNCAyExlHh4Yhh5555oAAAJBAyRxhQr4=';
}

var faders = document.querySelectorAll('.fade');
if ('IntersectionObserver' in window && faders.length) {
    var io = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                obs.unobserve(entry.target);
            }
        });
    }, { rootMargin: '0px 0px -40px 0px' });
    faders.forEach(function (el) { io.observe(el); });
} else {
    faders.forEach(function (el) { el.classList.add('visible'); });
}
