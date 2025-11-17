/* This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
   Distributed under terms of the GPL3 license. */

/*
Handles view-model functionalities, collects arguments entered in fields, and  
calls server functions via WebSocket.
*/

let socket = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    initialize();
    
    processNotifications();

    // react to command
    document.addEventListener("click", function(event) {
        if (event.target.matches(".execute, input.execute")) {
            if (event.target.dataset.confirm) {
                if (confirm(event.target.dataset.confirm) == false) {
                    return;
                }
            }
            process(event.target);
        }
    });
    
    let debounceTimer;
    document.addEventListener("input", function(event) {
        if (event.target.matches(".execute, input.execute")) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                process(event.target);
            }, 400);
        }
    });

    // invert selection in multiple-selection fields
    document.addEventListener("click", function(event) {
        if (event.target.matches(".invert-selection")) {
            invertSelection(event.target.parentElement);
        }
    });

    // bring into view
    document.addEventListener("click", function(event) {
        if (event.target.matches(".bring_into_view")) {
            const containerId = event.target.dataset.container;
            setTimeout(function() {
                bringIntoView(containerId);
            }, 1000);
        }
    });

    // Show details on click
    document.addEventListener("click", function(event) {
        // Don't show details if clicking on an execute button
        if (event.target.closest(".execute")) return;
        
        const el = event.target.closest("[data-details]");
        if (!el) return;
        const details = el.dataset.details;
        if (details && details.trim() !== "") {
            alert(details);
        }
    });
});

// Initialize WebSocket connection
function initializeWebSocket() {
    // Check if Socket.IO is loaded
    if (typeof io === 'undefined') {
        console.error('Socket.IO library not loaded');
        setTimeout(initializeWebSocket, 100);
        return;
    }
    
    // Configure Socket.IO with reconnection settings
    socket = io({
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 10
    });
    
    socket.on('connect', function() {
        console.log('WebSocket connected');
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
    });
    
    socket.on('response', function(views) {
        Object.keys(views).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                element.outerHTML = views[key];
                handleAutoUpdate(key);
            } else if (key === '_notification') {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = views[key];
                document.body.appendChild(tempDiv);
            }
        });
        
        processNotifications();
        enable(true);
    });
    
    socket.on('connect_error', function(error) {
        console.error('WebSocket connection error:', error);
        enable(true);
    });
}

function process(sourceElement) {
    if (document.querySelectorAll(".execute.inactive").length > 0) return;
    
    const funcPath = sourceElement.dataset.func;
    const form = sourceElement.closest("form");
    const fieldset1 = sourceElement.closest("fieldset");
    const fieldset2 = sourceElement.closest(".fieldset");

    let wait = false;
    const args = {};
    
    // Extract vm and func from the func path (e.g., "start/ctl")
    const parts = funcPath.split('/');
    const vm = parts[0];
    const func = parts[1] || 'ctl';
    
    [form, fieldset1, fieldset2].forEach(function(container) {
        if (!container) return;
        container.querySelectorAll("input, select, textarea").forEach(function(elem) {
            const key = elem.name;
            if (key === undefined || key === "") return;

            // Handle select, textarea elements
            if (elem.matches("input[type='text'], textarea, select")) {
                args[key] = elem.value;
            } else if (elem.matches("input")) {
                const value = elem.value;
                
                // Case multiple selected options
                if (elem.type === "checkbox") {
                    if (!args.hasOwnProperty(key)) {
                        args[key] = [];
                    }
                    if (elem.checked) {
                        args[key].push(value);
                    }
                } else if (elem.type === "file") {
                    const files = elem.files;
                    const filesCount = files.length;
                    if (filesCount === 0) return;
                    wait = true;
                    let fileUpload = 0;

                    for (let i = 0; i < files.length; i++) {
                        const file = files[i];
                        const fileReader = new FileReader();
                        const filename = file.name;

                        fileReader.onload = function(event) {
                            if (!args[key]) {
                                args[key] = {
                                    "names": [],
                                    "bytes": []
                                };
                            }
                            
                            args[key]["names"].push(filename);
                            args[key]["bytes"].push(event.target.result);
                            
                            fileUpload++;
                            if (fileUpload === filesCount) {
                                wait = false;
                            }
                        };
                        fileReader.readAsDataURL(file);
                    }
                } else {
                    args[key] = value;
                }
            }
        });
    });

    // triggers
    const param = sourceElement.dataset.param;
    if (param) {
        args[param] = sourceElement.dataset.value;
    }

    function waitAndExecute() {
        if (!wait) {
            execute(vm, func, args);
        } else {
            // TODO: progress visualization
            setTimeout(waitAndExecute, 1000);
        }
    }

    waitAndExecute();
}

// initialize module (extract view-model, function, and arguments from the URL)
function initialize() {
    enable(false);

    const parts = window.location.pathname.split('/');
    const vm = parts[1];
    const func = parts[2];

    const params = {};
    const searchParams = new URLSearchParams(window.location.search);
    searchParams.forEach(function(value, key) {
        params[key] = value;
    });

    execute(vm, func, params);
}

// execute a command and refresh view via WebSocket
function execute(vm, func, args) {
    if (!socket) {
        console.error("WebSocket not initialized");
        enable(true);
        return;
    }
    
    // If not connected, wait for connection
    if (!socket.connected) {
        console.log("Waiting for WebSocket connection...");
        socket.once('connect', function() {
            socket.emit('execute', {
                vm: vm,
                func: func,
                args: args
            });
        });
        return;
    }
    
    // Send command via WebSocket
    socket.emit('execute', {
        vm: vm,
        func: func,
        args: args
    });
}

// handle auto-update
const processedAutoUpdates = new Set();
function handleAutoUpdate(key) {
    if (processedAutoUpdates.has(key)) return;
    processedAutoUpdates.add(key);
    
    const updatedElement = document.getElementById(key);
    updatedElement.querySelectorAll('[data-autoupdatedelay]')
        .forEach(elem => {
            const delay = elem.dataset.autoupdatedelay;
            setTimeout(function() { 
                processedAutoUpdates.delete(key); 
                process(elem);
            }, delay);
        });
}

// process notifications and show alerts
function processNotifications() {
    const notifications = document.querySelectorAll('[data-alert]');
    notifications.forEach(elem => {
        const message = elem.dataset.alert;
        if (message && message.trim() !== "") {
            alert(message);
        }
        elem.remove();
    });
}

// enable or disable controls   
function enable(active) {
    controls = document.querySelectorAll(".execute");
    if (active) {
        controls.forEach(el => el.classList.remove("inactive"));
    }
    else {
        controls.forEach(el => el.classList.add("inactive"));
    }
}