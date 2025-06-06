async function loadConfig(filename) {
    try {
        const response = await fetch(filename);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error loading config.json:', error);
        return null;
    }
}