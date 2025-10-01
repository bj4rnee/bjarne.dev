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
    span.classList.add('animated-item');
    element.appendChild(span);

    setTimeout(() => {
      span.style.visibility = 'visible';
    }, delayPerCharacter * index);
  });
}

function randomAnimateText(className, duration) {
  const elements = document.getElementsByClassName(className);

  for (let element of elements) {
    const text = element.textContent;
    const totalDuration = duration || 1000;
    const randomDelays = [];

    for (let i = 0; i < text.length; i++) {
      randomDelays.push(Math.random() * totalDuration);
    }

    element.innerHTML = '';
    element.style.visibility = 'visible';

    // span for each char
    text.split('').forEach((char, index) => {
      const span = document.createElement('span');
      span.textContent = char;
      span.classList.add('animated-item');
      element.appendChild(span);

      setTimeout(() => {
        span.style.visibility = 'visible';
      }, randomDelays[index]);
    });
  }
}

function randomAnimateIcons(className, duration) {
  const elements = document.getElementsByClassName(className);

  for (let element of elements) {
    const icons = element.querySelectorAll('.fa-li i');
    const totalDuration = duration || 1000;
    const randomDelays = [];

    for (let i = 0; i < icons.length; i++) {
      randomDelays.push(Math.random() * totalDuration);
    }

    icons.forEach((icon, index) => {
      setTimeout(() => {
        icon.style.visibility = 'visible';
      }, randomDelays[index]);
    });
  }
}

function niceRandomColor() {
  const randomInt = (min, max) => {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  };
  return `hsl(${randomInt(0, 360)},${randomInt(42, 98)}%,${randomInt(40, 90)}%)`;

}

function getRandomHexColor() {
  return `#${Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0')}`;
}

function setRandomGDColor() {
  document.documentElement.style.setProperty('--gd-1', niceRandomColor());
  document.documentElement.style.setProperty('--gd-0', niceRandomColor());
  document.documentElement.style.setProperty('--gd-2', niceRandomColor());
  document.documentElement.style.setProperty('--gd-3', niceRandomColor());
}

function replaceSpacesWithNbsp(className) {
  const elements = document.getElementsByClassName(className);
  
  for (const el of elements) {
    el.innerHTML = el.innerHTML.replace(/ /g, '&nbsp;');
  }
}

window.onload = function () {
  setRandomGDColor();
  replaceSpacesWithNbsp('animation');
  animateText('cli_animation', 1500);
  setTimeout(() => { randomAnimateText('animation', 4000); }, 1500);
  setTimeout(() => { randomAnimateIcons('icon_animation', 1500); }, 1500);

};
