const { ipcRenderer } = require('electron');

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const logoButton = document.getElementById('logo-button');
    const mainOverlay = document.getElementById('main-overlay');
    const minimizeButton = document.getElementById('minimize-button');
    const closeButton = document.getElementById('cancel-button');
    const captureButton = document.getElementById('capture-button');
    
    // UI containers for managing different states
    const captureContainer = document.getElementById('capture-container');
    const loader = document.getElementById('loader');
    const responseContainer = document.getElementById('response-container');

    // Display user ID in the overlay (auto-refresh every 500ms)
    const userIdDisplay = document.getElementById("user-id-display");
    const updateUserIdDisplay = () => {
        const userId = window.userId || localStorage.getItem("user_mobile") || "unknown";
        if (userIdDisplay) {
            userIdDisplay.innerText = `User: ${userId}`;
        }
    };
    updateUserIdDisplay();
    setInterval(updateUserIdDisplay, 500); // auto-refresh every 500ms

    // --- State & Window Management ---

    // When the LOGO is clicked: expand the window and show the main UI
    logoButton.addEventListener('click', () => {
        // 1. Tell the main process to make the window bigger
        ipcRenderer.send('expand-window');
        // 2. Show the main overlay and hide the logo
        mainOverlay.classList.remove('hidden');
        logoButton.classList.add('hidden');
    });

    // When the CLOSE button on the overlay is clicked: shrink the window back to the logo
    closeButton.addEventListener('click', () => {
        // 1. Tell the main process to make the window smaller
        ipcRenderer.send('shrink-window');
        // 2. Hide the main overlay and show the logo again
        mainOverlay.classList.add('hidden');
        logoButton.classList.remove('hidden');
        ipcRenderer.send('reset-ui');
    });

    // The minimize button works as before
    minimizeButton.addEventListener('click', () => ipcRenderer.send('minimize-window'));

    // --- Core Application Logic (This part is unchanged) ---
    captureButton.addEventListener('click', async () => {
        captureContainer.classList.add('hidden');
        responseContainer.classList.add('hidden');
        loader.classList.remove('hidden');
        captureButton.disabled = true;

        try {
            const captureResult = await ipcRenderer.invoke('capture-screen');
            if (!captureResult || !captureResult.imageBase64 || captureResult.imageBase64.length < 1000) {
                throw new Error("⚠️ Screen capture failed — empty or invalid image data.");
            }
            console.log("✅ Captured base64 length:", captureResult.imageBase64.length);

            const userId = window.userId || localStorage.getItem("user_mobile") || "unknown";
            const userContext = captureResult.userContext;

            console.log("📤 Sending vision request with user ID:", userId);
            console.log("📤 Merged user context:", userContext.slice(0, 200));

            const response = await fetch("http://localhost:5050/api/vision/advice", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    image_base64: captureResult.imageBase64,
                    user_context: userContext,
                    mobile_number: userId
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API Error ${response.status}: ${errorText.slice(0, 200)}`);
            }

            const result = await response.json();
            console.log("✅ AI response received:", result);
            responseContainer.innerHTML = result?.advice
                ? result.advice.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>')
                : "No response from AI.";
            responseContainer.scrollTop = 0;
            
        } catch (error) {
            responseContainer.innerText = `An error occurred: ${error.message}`;
        } finally {
            loader.classList.add('hidden');
            responseContainer.classList.remove('hidden');
            // The UI state is now "stuck" on the response. The user must click the 
            // close (shrink) button to start a new capture.
        }
    });
});