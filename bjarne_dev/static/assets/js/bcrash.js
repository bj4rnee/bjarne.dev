function recentArray() {
    this.maxLength = 15;
}

recentArray.prototype = Object.create(Array.prototype);

recentArray.prototype.push = function (element) {
    Array.prototype.push.call(this, element);
    while (this.length > this.maxLength) {
        this.shift();
    }
}

const base = 1.057;
var balance = 1000.00;
var multiplier = 1.00;
var bet = 0.00;
var recent = new recentArray()

var running = false;
var crashed = false;
var cashed = false;
let updateInterval = null;
let autoInterval = null;
let elapsedTime = 0;

const width = 750;
const height = 500;
const margin = {
    left: 25,
    right: 25,
    top: 10,
    bottom: 25,
};

document.getElementById("balance").innerHTML = "&#x1F9CA; " + balance.toFixed(2);

const svg = d3.select("#graph_wrapper")
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${margin.left}, ${margin.top})`);

// graph area minus margins
const graphWidth = width - margin.left - margin.right;
const graphHeight = height - margin.top - margin.bottom;

let xMax = 10; // x axis start is 10 sec
let yMax = Math.pow(base, xMax);

const xScale = d3.scaleLinear()
    .domain([0, xMax])
    .range([0, graphWidth]);

const yScale = d3.scaleLinear()
    .domain([1, yMax])
    .range([graphHeight, 0]);

const xAxis = svg.append("g")
    .attr("transform", `translate(0, ${graphHeight})`)
    .call(d3.axisBottom(xScale).ticks(4));

const yAxis = svg.append("g")
    .call(d3.axisLeft(yScale).ticks(4));

// init function data
let data = d3.range(0, 0.1, 0.1).map(x => ({ x: x, y: Math.pow(base, x) }));

// line generator
const line = d3.line()
    .x(d => xScale(d.x))
    .y(d => yScale(d.y))
    .curve(d3.curveMonotoneX);

const path = svg.append("path")
    .datum(data)
    .attr("fill", "none")
    .attr("stroke", "white")
    .attr("stroke-width", 3)
    .attr("d", line);

const overlayText = svg.append("text")
    .attr("x", graphWidth / 2)
    .attr("y", graphHeight / 2)
    .attr("text-anchor", "middle")
    .attr("dy", ".35em")
    .attr("font-size", "100px")
    .style("visibility", "hidden");

function interpColor(y) {
    if (y == 0.00) {
        return "#fd5d93";
    } else if (y <= 1.05) {
        return "#777777";  // gray
    } else if (y <= 2) {
        return d3.interpolateRgb("#777777", "#1d8cf8")((y - 1.05) / 0.95);
    } else if (y <= 4) {
        return d3.interpolateRgb("#1d8cf8", "#b31df8")((y - 2) / 2);
    } else if (y <= 6.5) {
        return d3.interpolateRgb("#b31df8", "#f81df1")((y - 4) / 2.5);
    } else if (y <= 10) {
        return d3.interpolateRgb("#f81df1", "#fce527")((y - 6.5) / 3.5);
    } else if (y <= 25) {
        return d3.interpolateRgb("#fce527", "#fc8a27")((y - 10) / 15);
    } else {
        return "#fc8a27";
    }
}

function updateOverlayText(newY) {
    overlayText.selectAll("tspan").remove();
    overlayText.style("font-family", "monospace");

    if (crashed) {
        overlayText.append("tspan")
            .attr("fill", "#fd5d93")
            .attr("font-size", `${(width/7.5)-20}px`)
            .text(`crashed @ ${newY.toFixed(2)}x`);
        path.attr("stroke", "#fd5d93");
    } else if (cashed) {
        overlayText.append("tspan")
            .attr("fill", "#00f2c3")
            .attr("font-size", `${(width/7.5)-20}px`)
            .text(`cashout @ ${newY.toFixed(2)}x`);
        path.attr("stroke", "#00f2c3");
    } else {
        overlayText.append("tspan")
            .attr("fill", "#dfdfdf")
            .attr("font-size", "100px")
            .text(newY.toFixed(2));
        overlayText.append("tspan")
            .attr("fill", "#777777")
            .attr("font-size", "100px")
            .text("x");
    }
    overlayText.style("visibility", "visible");
}

function updateGraph(elapsedTimeInSeconds) {
    const newY = Math.pow(base, elapsedTimeInSeconds);
    const newColor = interpColor(newY)
    data.push({ x: elapsedTimeInSeconds, y: newY });

    updateOverlayText(newY, crashed);

    // if current time exceeds initial xMax (10 seconds), update x scale
    if (elapsedTimeInSeconds > xMax) {
        xMax = elapsedTimeInSeconds;
        yMax = Math.pow(base, xMax);
        xScale.domain([0, xMax]);
        yScale.domain([1, yMax]);
        xAxis.transition().duration(180).call(d3.axisBottom(xScale).ticks(4));
        yAxis.transition().duration(180).call(d3.axisLeft(yScale).ticks(4));
    }

    path.datum(data)
        .attr("d", line)
        .attr("stroke", newColor);
}

function updateRecent() {
    const recentDispl = document.getElementById('recent_displ');

    // clear
    recentDispl.innerHTML = '';

    // new div for each recent value
    recent.forEach(value => {
        const valueDiv = document.createElement('div');
        valueDiv.style.color = interpColor(value);
        valueDiv.textContent = `${value.toFixed(2)}x`;
        recentDispl.appendChild(valueDiv);
    });
}

// generate normally distributed random variable (mean = 0, stddev = 1)
function generateNormalRandom() {
    let u1 = Math.random();
    let u2 = Math.random();

    // Box-Muller transform
    let z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    return z0;
}

// generate log-normally distributed random variable with sigma = 1
function generateLogNormalRandom(sigma) {
    // mean = 0 for simplicity
    let normalRandom = generateNormalRandom();
    return Math.exp(sigma * normalRandom);
}

// gen exponentially distributed random variable
function generateExponentialRandom(lambda) {
    // uniform random number between 0 and 1
    let u = Math.random();
    // inverse transform sampling method
    return -Math.log(1 - u) / lambda;
}

function start() {
    if (running) {
        return;
    }
    cashed = false;
    crashed = false;
    multiplier = 1.00;
    elapsedTime = 0;
    running = true;

    bet = Number(Math.abs(Number(document.getElementById("input_bet").value)).toFixed(2));
    let auto_co = Number(Math.abs(Number(document.getElementById("auto_co").value)).toFixed(2));
    if (balance - bet < 0) {
        document.getElementById("bet").innerHTML = "place bet";
        running = false;
        return;
    }
    balance = Math.round((balance - bet + Number.EPSILON) * 100) / 100;
    document.getElementById("balance").innerHTML = "&#x1F9CA; " + balance.toFixed(2);

    const expValue = Math.max(1.00, generateExponentialRandom(0.2));

    xMax = 10;
    yMax = Math.pow(base, xMax);
    xScale.domain([0, xMax]);
    yScale.domain([1, yMax]);
    xAxis.transition().duration(300).call(d3.axisBottom(xScale).ticks(4));
    yAxis.transition().duration(300).call(d3.axisLeft(yScale).ticks(4));

    // clear previous data & reset graph
    data = d3.range(0, 0.1, 0.1).map(x => ({ x: x, y: Math.pow(base, x) })); // re-init data array
    path.datum(data).attr("d", line);  // clear path

    const startTime = performance.now();
    updateOverlayText(0.00);
    overlayText.style("visibility", "visible");

    // instant crash
    if (expValue == 1) {
        crash()
        return;
    }

    updateInterval = setInterval(() => {
        const currentTime = performance.now();
        const elapsedTimeInSeconds = (currentTime - startTime) / 1000;
        elapsedTime = elapsedTimeInSeconds;
        let y = Math.pow(base, elapsedTimeInSeconds);
        updateGraph(elapsedTimeInSeconds);

        // auto cashout
        if (elapsedTimeInSeconds > 90) {
            cashout(elapsedTimeInSeconds);
        }
        if (y >= auto_co && auto_co != 0) {
            cashout()
            return;
        }
        // crash
        if (expValue <= y) {
            crash()
            return;
        }

    }, 60); // update interval

}

async function cashout() {
    if (!running) {
        return;
    }
    multiplier = Math.round((Math.pow(base, elapsedTime) + Number.EPSILON) * 100) / 100;
    if (multiplier == 1) {
        return;
    }
    //console.log("cashout");
    running = false;
    cashed = true;
    clearInterval(updateInterval);
    document.getElementById("bet").innerHTML = "place bet";

    balance = Math.round(((balance + (multiplier * bet)) + Number.EPSILON) * 100) / 100;
    document.getElementById("balance").innerHTML = "&#x1F9CA; " + balance.toFixed(2);
    recent.push(multiplier);
    updateOverlayText(multiplier);
    await new Promise(r => setTimeout(r, 1200));
    updateRecent();
    cashed = false;
    overlayText.style("visibility", "hidden");
    path.datum([]).attr("d", null);  //  remove line
}

async function crash() {
    if (!running) {
        return;
    }
    running = false;
    crashed = true;
    clearInterval(updateInterval);
    document.getElementById("bet").innerHTML = "place bet";

    multiplier = Math.round((Math.pow(base, elapsedTime) + Number.EPSILON) * 100) / 100;
    if (elapsedTime == 0) {
        multiplier = 0.00;
    }
    recent.push(multiplier);
    updateOverlayText(multiplier);
    await new Promise(r => setTimeout(r, 1200));
    updateRecent();
    crashed = false;
    overlayText.style("visibility", "hidden");
    path.datum([]).attr("d", null);
}

function button_press() {
    if (!running) {
        document.getElementById("bet").innerHTML = "cashout";
        start()
    } else {
        document.getElementById("bet").innerHTML = "place bet";
        cashout()
    }
}

function half_bet() {
    let new_bet = Number(Math.abs(Number(document.getElementById("input_bet").value)).toFixed(2));
    new_bet = new_bet / 2;
    document.getElementById("input_bet").value = new_bet.toFixed(2);
}

function double_bet() {
    let new_bet = Number(Math.abs(Number(document.getElementById("input_bet").value)).toFixed(2));
    new_bet = new_bet * 2;
    document.getElementById("input_bet").value = new_bet.toFixed(2);
}

function max_bet() {
    let new_bet = balance;
    document.getElementById("input_bet").value = new_bet.toFixed(2);
}

function toggle_auto(cb) {
    if (cb.checked) {
        autoInterval = setInterval(() => {
            if (!running && !crashed && !cashed) {
                document.getElementById("bet").innerHTML = "cashout";
                start();
             }
        }, 1200);
    } else {
        clearInterval(autoInterval);
        document.getElementById("bet").innerHTML = "cashout";
    }
}

function scaleBcrash() {
  const wrapper = document.querySelector('#bcrash_wrapper');
  if (!wrapper) return;

  const baseWidth = wrapper.scrollWidth + 4; // 4px border
  const viewport = window.innerWidth;
  const scale = Math.min(viewport / baseWidth, 1); // never upscale

  wrapper.style.transform = `scale(${scale})`;
}

window.addEventListener('load', scaleBcrash);
window.addEventListener('resize', scaleBcrash);
window.addEventListener('orientationchange', scaleBcrash);