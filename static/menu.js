
// Copyright 2021 Johnathan Pennington | All rights reserved.


// HTML elements
let mobileMenuIsOpen = false;
let mobileMenuOpenImg = document.getElementById('menu-button-open-img');
let mobileMenuClosedImg = document.getElementById('menu-button-closed-img');
let menuBar = document.getElementById('menu-bar');
let menuItems = document.querySelectorAll('.menu-items a');

// Event listeners
window.addEventListener('resize', resizeWindow);
mobileMenuOpenImg.addEventListener('click', function() {
    mobileMenuIsOpen = false;
    resizeWindow();
});
mobileMenuClosedImg.addEventListener('click', function() {
    mobileMenuIsOpen = true;
    resizeWindow();
});
document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobileMenuIsOpen) {
        event.preventDefault();
        mobileMenuIsOpen = false;
        resizeWindow();
    };
});

resizeWindow();

function resizeWindow() {
    if (window.innerWidth < 640) {  // narrow/mobile display
        document.body.style.paddingTop = '0';
        for (menuItem of menuItems) {
            menuItem.style.display = 'block';
            menuItem.style.textAlign = 'left';
        };
        if (mobileMenuIsOpen) {
            menuBar.style.display = 'block';
            menuBar.style.height = '100%';
            menuBar.style.paddingTop = '6em';
            menuBar.style.textAlign = 'left';
            menuBar.style.backgroundColor = 'hsla(0, 0%, 0%, 85%)';
            mobileMenuClosedImg.style.display = 'none';
            mobileMenuOpenImg.style.display = 'block';
        } else {  // Mobile menu is closed.
            menuBar.style.display = 'none';
            mobileMenuClosedImg.style.display = 'block';
            mobileMenuOpenImg.style.display = 'none';
        };
    } else {  // wide/desktop display
        document.body.style.paddingTop = '4em';
        for (menuItem of menuItems) {
            menuItem.style.display = 'inline-block';
            menuItem.style.textAlign = 'center';
        };
        menuBar.style.display = 'block';
        menuBar.style.height = 'auto';
        menuBar.style.paddingTop = '0';
        mobileMenuClosedImg.style.display = 'none';
        mobileMenuOpenImg.style.display = 'none';
        menuBar.style.backgroundColor = 'hsla(0, 0%, 0%, 100%)';
        mobileMenuIsOpen = false;
    };
};
