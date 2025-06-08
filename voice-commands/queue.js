async function addToQueue(queueName, message) {
    try {
        const controller = new AbortController();
        setTimeout(() => controller.abort(), 5000);
        
        const config = await loadConfig("config.json");
        const queueUrl = config.QUEUE_URL;
        const body = {
            message: JSON.stringify(message)
        };

        console.log("Adding message to queue: " + queueName);
        console.log("Message body: " + JSON.stringify(body));

        const response = await fetch(queueUrl + '/' + queueName, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
            signal: controller.signal
        });

        console.log("Message queue response: " + JSON.stringify(response));

        return response;
    } catch (error) {
        console.error('Error adding message to queue:' + queueName, error);
        throw error; // Re-throw to allow caller to handle the error
    }
}