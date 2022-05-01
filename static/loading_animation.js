
// Copyright 2021 Johnathan Pennington | All rights reserved.


// HTML
// <button class="start-loading-animation">start1</button>
// <button class="start-loading-animation">start2</button>
// <button class="stop-loading-animation">stop1</button>
// <canvas id="loading-animation" style="width: 100px; display: none; position: fixed; touch-action: none; top: 50%; left: 50%; -ms-transform: translate(-50%, -50%); transform: translate(-50%, -50%)">Your browser does not support the canvas element.</canvas>

const canvas1 = document.getElementById('loading-animation');
canvas1.height = canvas1.width;
const ctx1 = canvas1.getContext('2d');
ctx1.translate(canvas1.width / 2, canvas1.width / 2);
ctx1.scale(canvas1.width, canvas1.width);

var animating = false;
var lastFrame = -1;
var startLoadTimeoutId;

// Custom settings
var shells = [
    {length: 0.5, color: 'hsl(255, 100%, 50%)', radPos: 0.5, speed: 4 / 4, },
    {length: 0.5, color: 'hsl(270, 100%, 50%)', radPos: 0.5, speed: 5 / 4, },
    {length: 0.5, color: 'hsl(285, 100%, 50%)', radPos: 0.5, speed: 6 / 4, },
    {length: 0.5, color: 'hsl(300, 100%, 50%)', radPos: 0.5, speed: 7 / 4, },
];
// Array ordered from inner shells to outer shells.
// Length of 1 is full rotation around.
// RadPos goes from 0-1, with 0 and 1 pointing due right. Increasing radPos causes clockwise rotation.
// Speed is rotations per second.
//
const centerCircleColor = 'hsl(240, 100%, 50%)';
const centerCircleDiameter = 0.4; // 1 is full diameter of canvas.
const shellHeight = (1 - centerCircleDiameter - 2 / canvas1.width) / shells.length / 2; // 1 pixel radius cushion
const startDelay = 0.5  // seconds

// Don't show animation after back button.
window.addEventListener("pagehide", stopLoading);

for (element of document.getElementsByClassName('stop-loading-animation')) {
    element.addEventListener('click', stopLoading);
};
for (element of document.getElementsByClassName('start-loading-animation')) {
    element.addEventListener('click', showLoading);
};


function stopLoading() {
    clearTimeout(startLoadTimeoutId)
    canvas1.style.display = 'none';
    animating = false;
};


function showLoading() {
    clearTimeout(startLoadTimeoutId)
    startLoadTimeoutId = setTimeout(function() {
        canvas1.style.display = 'block';
        animating = true;
        window.requestAnimationFrame(animate);
    }, startDelay * 1000);
};


function animate(timestamp) {

    let intervalSinceLastFrame = timestamp / 1000 - lastFrame;
    if (lastFrame === -1) { intervalSinceLastFrame = 0; };
    lastFrame = timestamp / 1000;

    // Clear canvas.
    ctx1.clearRect(canvas1.width / -2, canvas1.height / -2, canvas1.width, canvas1.height)

    // Move shells
    for (let shellNum = 0; shellNum < shells.length; shellNum++) {
        shells[shellNum].radPos = mod(shells[shellNum].radPos + intervalSinceLastFrame * shells[shellNum].speed, 1);
    };

    // Draw shells.
    for (let shellNum = shells.length - 1; shellNum >= 0; shellNum--) {
        ctx1.save();
        ctx1.rotate(shells[shellNum].radPos * 2 * Math.PI);
        ctx1.fillStyle = shells[shellNum].color;
        ctx1.beginPath();
        ctx1.arc(0, 0, centerCircleDiameter / 2 + shellHeight * shellNum, 0, shells[shellNum].length * 2 * Math.PI, false);
        ctx1.arc(0, 0, centerCircleDiameter / 2 + shellHeight * (shellNum + 1) + 1 / canvas1.width, shells[shellNum].length * 2 * Math.PI, 0, true);
        ctx1.fill();
        ctx1.restore();
    };

    // Draw center circle.
    ctx1.save();
    ctx1.fillStyle = centerCircleColor;
    ctx1.beginPath();
    ctx1.arc(0, 0, centerCircleDiameter / 2 + 1 / canvas1.width, 0, 2 * Math.PI, false); // Adds 1 pixel to defined circleRadius.
    ctx1.fill();
    ctx1.restore();

    if (animating) {
        window.requestAnimationFrame(animate);
    };
};


function mod(a, n) { return ((a % n) + n) % n; }; // Always returns positive result.
