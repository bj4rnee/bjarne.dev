// var time = 500000 // ms

// var progressBar = document.getElementById("time-left");

// var interval = 100; // Update every 100 milliseconds
// var totalTicks = time / interval; 
// var progressLeft = 100; // Start at 100%

// function updateProgress() {
//     progressLeft-= 10;
//     progressBar.value = progressLeft; 
    
//     if (progressLeft <= 0) {
//         clearInterval(timerInterval); 
//     }
// }

// var timerInterval = setInterval(updateProgress, 1000);
const timerFreq = 50; // ms
var time = 5000; // 10 seconds in milliseconds
var progressBar = document.getElementById('time-left').querySelector('span');

function updateProgressBarColor(percentage) {
  // Arbitrary RGB colors: Start color and End color
  var endColor = { r: 0, g: 242, b: 194 }; // Orange
  var startColor = { r: 253, g: 93, b: 147 }; // Blue
  
  // Interpolate between startColor and endColor based on percentage
  var r = Math.round(startColor.r + (endColor.r - startColor.r) * (percentage / 100));
  var g = Math.round(startColor.g + (endColor.g - startColor.g) * (percentage / 100));
  var b = Math.round(startColor.b + (endColor.b - startColor.b) * (percentage / 100));
  
  return `rgb(${r}, ${g}, ${b})`;
}


function startTimer() {
  time = 5000;
    // var start = Date.now();
    // progressBar.value = 100;
    // var interval = setInterval(function() {
    //     var elapsed = Date.now() - start;
    //     var progress = Math.max(0, 100 - (elapsed / time) * 100);
    //     progressBar.value = progress;

    //     if (elapsed >= time) {
    //         clearInterval(interval);
    //     }
    // }, 1000); // Update every 100ms for smooth animation
    let initialTime = time;
    progressBar.style.width = '100%';
    progressBar.style.backgroundColor = updateProgressBarColor(100);
      
      // Clear any previous intervals (optional, for safety)
      clearInterval(window.progressInterval);

      // Start the countdown
      window.progressInterval = setInterval(function() {
        time -= timerFreq; // decrement time by 100ms

        // Calculate the percentage of time remaining
        var percentage = (time / initialTime) * 100;
        
        // Update the progress bar width based on the remaining percentage
        progressBar.style.width = percentage + '%';
        progressBar.style.backgroundColor = updateProgressBarColor(percentage);

        // Stop when time runs out
        if (time <= 0) {
          clearInterval(window.progressInterval);
          time = 0; // Ensure time doesn't go below 0
        }

      }, timerFreq); // Update every 100ms
}

//startTimer();
setInterval(startTimer, 6000);