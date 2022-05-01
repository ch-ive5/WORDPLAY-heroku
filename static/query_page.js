
// Copyright 2021 Johnathan Pennington | All rights reserved.


// HTML elements
const randomButton = document.getElementById('random-button');
const randTextSpans = document.querySelectorAll('.rand-text span');
const formTextareas = document.querySelectorAll('textarea');
const calculateButton = document.getElementById('calculate-button');
const errorMessage = document.getElementById('error');


// "I'm feeling random" state/settings.
var intervalId;
var animationOn = false;
var randButtonClicked = false;
var randButtonClickableTimestamp = null;
const animationMinMsecs = 700;


// Event listeners
randomButton.addEventListener('click', event => {

    if (randButtonClicked) { return; };
    randButtonClicked = true;

    let timeTillClick = animationMinMsecs;
    if (randButtonClickableTimestamp !== null) { timeTillClick = randButtonClickableTimestamp - Date.now(); };

    if (timeTillClick > 0) {
        event.preventDefault();
        startRandTextAnimation();
        setTimeout(function() { randomButton.click(); }, timeTillClick);
    };
});

randomButton.addEventListener('mouseover', startRandTextAnimation);

randomButton.addEventListener('mouseleave', () => {
    if (randButtonClicked === false) {
        stopRandTextAnimation();
    };
});

window.addEventListener('pagehide', () => {  // Don't show animation after back button.
    randButtonClicked = false;
    stopRandTextAnimation();
});

for (textarea of formTextareas) {  // Enter key sends form.
    textarea.addEventListener('keydown', event => {
        if (event.keyCode === 13) {
            event.preventDefault();
            calculateButton.click();
        };
    });
};


// Scroll to error.
if (errorMessage.innerText !== '') { errorMessage.scrollIntoView(false); };


function randChoice(array) {
    index = Math.floor(Math.random() * array.length);
    return array[index];
};

function stopRandTextAnimation() {
    animationOn = false;
    randButtonClickableTimestamp = null;
    clearInterval(intervalId);
};

function startRandTextAnimation() {
    if (animationOn) { return; };
    animationOn = true;
    randButtonClickableTimestamp = Date.now() + animationMinMsecs;
    clearInterval(intervalId);
    intervalId = setInterval(randomText, 70);
};

// "I'm feeling random" animation.
function randomText() {
    for (randSpan of randTextSpans) {
        let randHue = 86;
        if (Math.random() < 0.5) { randHue = 180; };
        let randLightness = 70;
        if (Math.random() < 0.5) { randLightness = 100; };
        randSpan.style.color = `hsl(${randHue}, 100%, ${randLightness}%)`;
        let randType = Math.random();
        if (randSpan.innerText === 'I' || randSpan.innerText === 'i' || randSpan.innerText === '1' || randSpan.innerText === '!') {
            randSpan.innerText = randChoice(['I', 'i', '1', '!']);
        } else if (randSpan.innerText === 'A' || randSpan.innerText === 'a' || randSpan.innerText === '@' || randSpan.innerText === '4') {
            randSpan.innerText = randChoice(['A', 'a', '@', '4']);
        } else if (randSpan.innerText === 'E' || randSpan.innerText === 'e' || randSpan.innerText === '3') {
            randSpan.innerText = randChoice(['E', 'e', '3']);
        } else if (randSpan.innerText === 'G' || randSpan.innerText === 'g' || randSpan.innerText === '9') {
            randSpan.innerText = randChoice(['G', 'g', '9']);
        } else if (randSpan.innerText === 'O' || randSpan.innerText === 'o' || randSpan.innerText === '0') {
            randSpan.innerText = randChoice(['O', 'o', '0']);
        } else if (randType < 0.5) {
            randSpan.innerText = randSpan.innerText.toLowerCase();
        } else {
            randSpan.innerText = randSpan.innerText.toUpperCase();
        };
    };
};
