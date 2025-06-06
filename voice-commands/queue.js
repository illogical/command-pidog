async function addToQueue(queueName, message) {
    try {
        const controller = new AbortController();
        setTimeout(() => controller.abort(), 10000);
        
        const config = await loadConfig("config.json");
        const queueUrl = config.QUEUE_URL;

        const response = await fetch(queueUrl + '/' + queueName, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message
            }),
            signal: controller.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error calling Ollama API:', error);
        throw error; // Re-throw to allow caller to handle the error
    }
}