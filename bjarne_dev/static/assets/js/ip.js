/*
 * ip debug page
 */
(function () {
    var dataEl = document.getElementById('ip_server_data');
    if (!dataEl) return;

    var payload = JSON.parse(dataEl.textContent);
    var PING_SAMPLES = 5;
    var EDGE_TARGET = '/static/favicon.svg';

    // probe images, verified to decode
    var AVIF_PROBE = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADrbWV0YQAAAAAAAAAhaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAAAAAAAOcGl0bQAAAAAAAQAAAB5pbG9jAAAAAEQAAAEAAQAAAAEAAAETAAAAIAAAAChpaW5mAAAAAAABAAAAGmluZmUCAAAAAAEAAGF2MDFDb2xvcgAAAABqaXBycAAAAEtpcGNvAAAAFGlzcGUAAAAAAAAAAQAAAAEAAAAQcGl4aQAAAAADCAgIAAAADGF2MUOBAAwAAAAAE2NvbHJuY2x4AAEADQAGgAAAABdpcG1hAAAAAAAAAAEAAQQBAoMEAAAAKG1kYXQSAAoIGAAGiAhoNCAyEh/3h4UV3///4sAAAJA1jjx+3A==';
    var WEBP_PROBE = 'data:image/webp;base64,UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==';
    var JXL_PROBE = 'data:image/jxl;base64,/wpHQCTYYyAAAHQAAuAoKipGxmAQgF8AAEToz4Qk4ox2AughlkBwAADYY1gAAHAAAuAgKipGxkgAfgEAEKFfEhIJRFhA4YklEBxgCA==';

    function text(value) {
        if (value === null || value === undefined) return 'n/a';
        if (value === true) return 'true';
        if (value === false) return 'false';
        return String(value);
    }

    function round(value, digits) {
        var f = Math.pow(10, digits || 1);
        return Math.round(value * f) / f;
    }

    function ms(value) {
        if (value === null || value === undefined || isNaN(value)) return null;
        return round(value) + ' ms';
    }

    function bytes(value) {
        if (!value) return value === 0 ? '0 B' : null;
        if (value < 1024) return value + ' B';
        return round(value / 1024) + ' KiB (' + value + ' B)';
    }

    function boolClass(value) {
        if (value === true) return ' ip_yes';
        if (value === false) return ' ip_no';
        return '';
    }

    // rtt rows min / avg / max get own color
    var SPREAD = /^min ([\d.]+) \/ avg ([\d.]+) \/ max ([\d.]+) ms$/;

    function spreadInto(el, m) {
        ['min', 'avg', 'max'].forEach(function (name, i) {
            var num = document.createElement('span');
            num.className = 'ip_' + name;
            num.textContent = m[i + 1];
            el.append((i ? ' / ' : '') + name + ' ', num);
        });
        el.append(' ms');
    }

    /* replace a sections rows, keep its heading */
    function fill(sectionId, values) {
        var section = document.getElementById(sectionId);
        if (!section) return;
        var old = section.querySelectorAll('.ip_row');
        for (var i = 0; i < old.length; i++) old[i].remove();

        Object.keys(values).forEach(function (key) {
            var row = document.createElement('div');
            row.className = 'ip_row';
            var k = document.createElement('span');
            k.className = 'ip_k';
            k.textContent = key;
            var v = document.createElement('span');
            v.className = 'ip_v' + boolClass(values[key]);
            var m = SPREAD.exec(text(values[key]));
            if (m) spreadInto(v, m);
            else v.textContent = text(values[key]);
            row.appendChild(k);
            row.appendChild(v);
            section.appendChild(row);
        });
    }

    function setRow(id, value, bad) {
        var el = document.getElementById(id);
        if (!el) return;
        el.textContent = value;
        el.className = 'ip_v' + (bad ? ' ip_bad' : '');
    }

    // ---------------------------------------------------------------- reverse dns
    setRow('ip_v_client_reverse_dns', 'resolving...', false);
    fetch('/ip/rdns', { cache: 'no-store' })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
            payload.client.reverse_dns = data.reverse_dns;
            setRow('ip_v_client_reverse_dns', text(data.reverse_dns), false);
        })
        .catch(function () {
            payload.client.reverse_dns = 'lookup failed';
            setRow('ip_v_client_reverse_dns', 'lookup failed', true);
        });

    // ------------------------------------------------------------------- browser
    // server stamps somewhere between request out and first byte back
    // using midpoint should exclude page load time
    function clockOffset() {
        var nav = performance.getEntriesByType('navigation')[0];
        var mid = nav && nav.responseStart
            ? performance.timeOrigin + (nav.requestStart + nav.responseStart) / 2
            : Date.now();
        return round(mid - payload.request.epoch_ms) + ' ms vs server';
    }

    function browserFacts() {
        var hints = navigator.userAgentData;
        var facts = {
            user_agent: navigator.userAgent,
            platform: (hints && hints.platform) || navigator.platform || null,
            mobile_hint: hints ? hints.mobile : null,
            languages: (navigator.languages || []).join(', ') || navigator.language || null,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
            clock_offset: clockOffset(),
            viewport: window.innerWidth + ' x ' + window.innerHeight,
            screen: window.screen.width + ' x ' + window.screen.height,
            pixel_ratio: window.devicePixelRatio,
            color_scheme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
            reduced_motion: matchMedia('(prefers-reduced-motion: reduce)').matches,
            cookies_enabled: navigator.cookieEnabled,
            secure_context: window.isSecureContext,
            cpu_threads: navigator.hardwareConcurrency || null,
            device_memory_gb: navigator.deviceMemory || null,
            do_not_track: navigator.doNotTrack || null,
            global_privacy_control: navigator.globalPrivacyControl === undefined
                ? null : navigator.globalPrivacyControl
        };

        var net = navigator.connection;
        if (net) {
            facts.net_type = net.effectiveType || null;
            facts.net_downlink = net.downlink ? net.downlink + ' Mbit/s' : null;
            facts.net_rtt = net.rtt ? net.rtt + ' ms' : null;
            facts.net_save_data = net.saveData;
        }
        return facts;
    }

    // ------------------------------------------------------------------- support
    function decodes(src) {
        return new Promise(function (resolve) {
            var img = new Image();
            img.onload = function () { resolve(img.width > 0); };
            img.onerror = function () { resolve(false); };
            img.src = src;
        });
    }

    function storageWorks() {
        try {
            localStorage.setItem('ip_probe', '1');
            localStorage.removeItem('ip_probe');
            return true;
        } catch (err) {
            return false;
        }
    }

    function supportFacts() {
        return {
            'crypto.subtle': !!(window.crypto && window.crypto.subtle),  // filelink needs this
            webassembly: typeof WebAssembly === 'object',
            avif: null,
            webp: null,
            jxl: null,
            local_storage: storageWorks(),
            clipboard_api: !!(navigator.clipboard && navigator.clipboard.writeText),
            service_worker: 'serviceWorker' in navigator,
            file_api: typeof Blob === 'function' && typeof File === 'function'
        };
    }

    // -------------------------------------------------------------------- timing
    function navigationFacts() {
        var nav = performance.getEntriesByType('navigation')[0];
        if (!nav) return { navigation_timing: 'unavailable' };

        var facts = {
            protocol: nav.nextHopProtocol || 'unknown',
            connection: nav.connectEnd === nav.connectStart ? 'reused' : 'new',
            dns: ms(nav.domainLookupEnd - nav.domainLookupStart),
            tcp_and_tls: ms(nav.connectEnd - nav.connectStart),
            tls_handshake: nav.secureConnectionStart
                ? ms(nav.connectEnd - nav.secureConnectionStart) : null,
            ttfb: ms(nav.responseStart - nav.requestStart),
            response_download: ms(nav.responseEnd - nav.responseStart),
            dom_ready: ms(nav.domContentLoadedEventEnd),
            transfer: bytes(nav.transferSize),
            body_on_wire: bytes(nav.encodedBodySize),
            body_decoded: bytes(nav.decodedBodySize)
        };
        if (nav.encodedBodySize > 0 && nav.decodedBodySize > 0) {
            var ratio = nav.decodedBodySize / nav.encodedBodySize;
            facts.compression = ratio > 1.02
                ? round(ratio, 2) + 'x'
                : 'none, response sent uncompressed';
        }
        return facts;
    }

    function pingOnce(url, method) {
        var start = performance.now();
        return fetch(url, { method: method, cache: 'no-store' }).then(function () {
            return performance.now() - start;
        });
    }

    /* sequential, samples do not measure each other */
    function pingSeries(url, method, count) {
        var seen = [];
        function step() {
            if (seen.length >= count) return Promise.resolve(seen);
            return pingOnce(url, method).then(function (dt) {
                seen.push(dt);
                return step();
            });
        }
        return step();
    }

    function spread(samples) {
        var min = Math.min.apply(null, samples);
        var sum = samples.reduce(function (a, b) { return a + b; }, 0);
        return {
            min: min,
            text: 'min ' + round(min) + ' / avg ' + round(sum / samples.length)
                + ' / max ' + round(Math.max.apply(null, samples)) + ' ms'
        };
    }

    function measure() {
        var timing = navigationFacts();
        payload.timing = timing;
        fill('ip_sec_timing', timing);

        var cb = '?p=' + Date.now() + '-' + Math.random().toString(36).slice(2);
        pingSeries('/ip/ping', 'GET', PING_SAMPLES).then(function (app) {
            timing.app_rtt = spread(app).text;
            fill('ip_sec_timing', timing);
            return pingSeries(EDGE_TARGET + cb, 'HEAD', PING_SAMPLES).then(function (edge) {
                var gap = spread(app).min - spread(edge).min;
                timing.edge_rtt = spread(edge).text;
                // static fetch never reaches webapp, therefore gap is django plus lsapi
                // both paths jitter
                timing.app_overhead = gap < 1 ? 'below jitter' : round(gap) + ' ms';
                fill('ip_sec_timing', timing);
            });
        }).catch(function () {
            timing.app_rtt = 'sampling failed';
            fill('ip_sec_timing', timing);
        });
    }

    // ---------------------------------------------------------------- geo lookup
    var geoBtn = document.getElementById('ip_geo_btn');
    var geoOut = document.getElementById('ip_geo');

    function showGeo(value) {
        geoOut.hidden = false;
        geoOut.textContent = value;
    }

    geoBtn.addEventListener('click', function () {
        if (payload.client.scope !== 'global') {
            showGeo('skipped, ' + payload.client.ip + ' is not globally routable');
            return;
        }
        geoBtn.disabled = true;
        geoBtn.textContent = 'looking up...';
        fetch('https://api.ipquery.io/' + encodeURIComponent(payload.client.ip), {
            mode: 'cors',
            cache: 'no-store'
        }).then(function (resp) {
            if (!resp.ok) throw new Error('provider returned HTTP ' + resp.status);
            return resp.json();
        }).then(function (data) {
            payload.geo = data;
            showGeo(JSON.stringify(data, null, 2));
        }).catch(function (err) {
            payload.geo = { error: String(err.message || err) };
            showGeo('lookup failed: ' + (err.message || err));
        }).then(function () {
            geoBtn.disabled = false;
            geoBtn.textContent = 'lookup again';
        });
    });

    // -------------------------------------------------------------------- copying
    function copy(value, icon) {
        navigator.clipboard.writeText(value).then(function () {
            icon.classList.remove('fa-copy');
            icon.classList.add('fa-check');

            // revert after 2 seconds
            setTimeout(function () {
                icon.classList.remove('fa-check');
                icon.classList.add('fa-copy');
            }, 2000);
        }).catch(function (err) {
            console.error('[Error]: copy failed.', err);
        });
    }

    document.getElementById('ip_copy_addr').addEventListener('click', function () {
        copy(payload.client.ip || '', document.getElementById('ip_copy_addr_icon'));
    });

    document.getElementById('ip_copy_json').addEventListener('click', function () {
        copy(JSON.stringify(payload, null, 2), document.getElementById('ip_copy_json_icon'));
    });

    // ----------------------------------------------------------------------- go
    payload.browser = browserFacts();
    fill('ip_sec_browser', payload.browser);

    var support = supportFacts();
    payload.support = support;
    fill('ip_sec_support', support);
    Promise.all([decodes(AVIF_PROBE), decodes(WEBP_PROBE), decodes(JXL_PROBE)])
        .then(function (results) {
            support.avif = results[0];
            support.webp = results[1];
            support.jxl = results[2];
            fill('ip_sec_support', support);
        });

    // navigation timings only complete once load has fired
    if (document.readyState === 'complete') {
        measure();
    } else {
        window.addEventListener('load', measure);
    }
})();
