function getCurrentTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
}

function animateText(elementId, duration) {
    const element = document.getElementById(elementId);
    const text = element.textContent;
    const delayPerCharacter = duration / text.length;

    // clear existing text in span
    element.innerHTML = '';
    text.split('').forEach((char, index) => {
      const span = document.createElement('span');
      span.textContent = char;
      span.classList.add('animated-char');
      element.appendChild(span);

      setTimeout(() => {
        span.style.visibility = 'visible';
      }, delayPerCharacter * index);
    });
  }

  window.onload = function() {
    animateText('cli_animation', 1500);
  };