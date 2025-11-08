/* This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
   Distributed under terms of the GPL3 license. */

/*
Animations for the background tiles. Currently deactivated because certain browsers do not display them properly.
*/

function getRandomColor() {
    return '#' + Array.from({ length: 6 }, () => '0123456789ABCDEF'[Math.floor(Math.random() * 16)]).join('');
}

function setRegularInterval(callback, base, variable) {
    const interval = base + Math.random() * variable;
    setTimeout(() => { callback(); setRegularInterval(callback, base, variable); }, interval);
}

function initializeGrid() {
    const grid = document.querySelector('.background-grid');
    const tiles = grid.querySelectorAll('.tile');
    if (tiles.length === 0) {
        Array.from({ length: tilesToCreate }, createTile);
    }
    //changeTilesColor();
    //updateBaseColor();
}

function updateBaseColor() {
    const second = new Date().getSeconds();
    const baseColors = ["#FF0000", "#FFFF00", "#00FF00", "#00FFFF", "#0000FF", "#FF00FF"];
    const interval = Math.floor(second / 10);

    colorBase = (Math.random() < 0.05) ? "#000000" :
        (Math.random() < 0.5) ? combineColors(colorBase, getRandomColor()) : baseColors[interval];
    
    if (Math.random() < 0.3) colorBasePart = Math.floor(Math.random() * 3);
}

function createTile() {
    const tile = document.createElement('div');
    const tileSize = Math.min(window.innerWidth, window.innerHeight) * ((Math.random() * 80 + 30) / 100);
    const grid = document.querySelector('.background-grid');

    tile.classList.add('tile');
    if (Math.random() < 0.5) tile.classList.add('tile-round');
    else if (Math.random() < 0.3) adjustTileSize(tile, tileSize);

    positionTile(tile, tileSize);
    
    tile.style.backgroundColor = combineColors(colorBase, getRandomColor());
    updateBaseColor();
    
    grid.appendChild(tile);
}

function adjustTileSize(tile, size) {
    const scale = Math.random() < 0.6 ? 0.5 : 0.3;
    tile.style.width = `${size * scale}px`;
    tile.style.height = `${size * scale}px`;
}

function positionTile(tile, size) {
    tile.style.position = 'absolute';
    tile.style.width = `${size}px`;
    tile.style.height = `${size}px`;
    randomX = Math.random() < 0.5 ? randomX : Math.random() * (window.innerWidth - size);
    randomY = Math.random() < 0.5 ? randomY : Math.random() * (window.innerHeight - size);
    tile.style.left = `${randomX}px`;
    tile.style.top = `${randomY}px`;
}

function createEmoji() {
    const categories = {
        cat2: ["☀️", "🌍", "🪐", "🛰️", "🌕", "🍌"],
        cat3: ["☕", "👾", "⭐", "💣", "👻", "😵‍💫", "🌘", "🔥", "🍌"],
        cat4: ["🍉", "🍇", "🍓", "🍔", "🍕", "🍦", "🍭", "🍌"],
        cat5: ["🌴", "🐒", "🦧", "🐘", "🐁", "🦉", "🕷️", "🦩", "🍌"],
        cat6: ["🦀", "🦑", "🐙", "🦈", "🐬", "🐟", "🐋", "🦐", "🦞", "🐠"],
    };
    const grid = document.querySelector('.background-grid');
    const category = categories[Object.keys(categories)[Math.floor(Math.random() * 5)]];
    const emojis = category.sort(() => 0.5 - Math.random()).slice(0, Math.floor(Math.random() * 3) + 1);

    emojis.forEach(symbol => {
        const tile = document.createElement('div');
        tile.classList.add('emoji');
        tile.innerHTML = symbol;
        tile.style.position = 'absolute';
        tile.style.left = `${Math.random() * 25}em`;
        tile.style.top = `${5 + Math.random() * 25}em`;
        grid.appendChild(tile);
    });
}

function changeTilesColor() {
    const tiles = document.querySelectorAll('.tile');
    const tile = tiles[Math.floor(Math.random() * tiles.length)];
    tile.style.backgroundColor = combineColors(colorBase, getRandomColor());
}

function combineColors(color1, color2) {
    return `#${[color1.slice(1, 3), color2.slice(3, 5), color1.slice(5, 7)].map((part, i) => i === colorBasePart ? color2.slice(i * 2 + 1, i * 2 + 3) : part).join('')}`;
}

function duplicateTiles() {
    const grid = document.querySelector('.background-grid');
    const tiles = Array.from(grid.querySelectorAll('.tile'));
    const tilesToDuplicate = Math.floor(tiles.length * 0.7);

    Array.from({ length: tilesToDuplicate }, () => {
        const originalTile = tiles[Math.floor(Math.random() * tiles.length)];
        const clone = originalTile.cloneNode(true);

        const tileWidth = parseFloat(originalTile.style.width || 0);
        const tileHeight = parseFloat(originalTile.style.height || 0);

        const offsetMultiplier = [0.2, 0.4, 0.6][Math.floor(Math.random() * 3)];

        const offsetType = Math.random();
        let offsetX = 0, offsetY = 0;

        if (offsetType < 0.25) {
            offsetY = tileHeight * offsetMultiplier * (Math.random() < 0.5 ? 1 : -1);
        } else if (offsetType < 0.5) {
            offsetX = tileWidth * offsetMultiplier * (Math.random() < 0.5 ? 1 : -1);
        } else {
            offsetX = tileWidth * offsetMultiplier * (Math.random() < 0.5 ? 1 : -1);
            offsetY = tileHeight * offsetMultiplier * (Math.random() < 0.5 ? 1 : -1);
        }

        const originalLeft = parseFloat(originalTile.style.left || 0);
        const originalTop = parseFloat(originalTile.style.top || 0);

        clone.style.left = `${originalLeft + offsetX}px`;
        clone.style.top = `${originalTop + offsetY}px`;

        grid.appendChild(clone);
    });
}


let colorBase = "#00FFFF";
let colorBasePart = 0;
let randomX = 0, randomY = 0, tilesToCreate = 8;

document.addEventListener('DOMContentLoaded', () => {
    initializeGrid();
    duplicateTiles();
    //setRegularInterval(initializeGrid, 4000, 3000);
    //if (Math.random() < 0.1) createEmoji();
});
