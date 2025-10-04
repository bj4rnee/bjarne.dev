document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        if (document.visibilityState === 'visible') {
            const token = document.querySelector('meta[name="visit-token"]').content;
            if (token) {
                fetch(`/incr-visit/?token=${encodeURIComponent(token)}`)
                    .catch(err => console.error('Failed to increment visit:', err));
            }
        }
    }, 250); // ms delay
});