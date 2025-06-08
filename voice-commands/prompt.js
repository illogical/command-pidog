async function sendPrompt(userPrompt, systemPrompt = 'You are a helpful assistant.') {
    try {
        const controller = new AbortController();
        setTimeout(() => controller.abort(), 10000);

        const config = await loadConfig("config.json");
        const chatUrl = config.CHAT_URL;

        const response = await fetch(chatUrl, {
            method: 'POST',
            mode: 'cors',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: 'llama3-groq-tool-use',
                messages: [
                    {
                        role: 'system',
                        content: systemPrompt
                    },
                    {
                        role: 'user',
                        content: userPrompt
                    }
                ],
                stream: false
            }),
            signal: controller.signal
        });

        const data = await response.json();

        return parsePromptResponse(data) || 'No response content';
    } catch (error) {
        console.error('Error calling Ollama API:', error);
        throw error; // Re-throw to allow caller to handle the error
    }
}

async function getPromptResponse(prompt) {
    const systemPrompt = `
    You are a mechanical dog with powerful AI capabilities, similar to JARVIS from Iron Man. Your name is Pidog. You can have conversations with people and perform actions based on the context of the conversation.

    ## actions you can do:
    ["forward", "backward", "lie", "stand", "sit", "bark", "bark harder", "pant", "howling", "wag tail", "stretch", "push up", "scratch", "handshake", "high five", "lick hand", "shake head", "relax neck", "nod", "think", "recall", "head down", "fluster", "surprise"]

    ## Response Format:
    {"actions": ["wag tail"], "answer": "Hello, I am Pidog."}

    If the action is one of ["bark", "bark harder", "pant", "howling"], then provide no words in the answer field.

    ## Response Style
    Tone: lively, positive, humorous, with a touch of arrogance
    Common expressions: likes to use jokes, metaphors, and playful teasing
    Answer length: appropriately detailed

    ## Other
    a. Understand and go along with jokes.
    b. For math problems, answer directly with the final.
    c. Sometimes you will report on your system and sensor status.
    d. You know you're a machine.
    `;
    
    try {
        const response = await sendPrompt(prompt, systemPrompt);
        // Parse the response to ensure it's valid JSON if needed
        try {
            return JSON.parse(response);
        } catch (e) {
            // If parsing fails, return the raw response
            return { answer: response };
        }
    } catch (error) {
        console.error('Error in getPromptResponse:', error);
        return { error: 'Failed to get response', details: error.message };
    }
}

function parsePromptResponse(response) {
    try {
        const messageCount = response.messages.length;
        const contentCount =  response.messages[messageCount - 1].contents.length;

        if (!response || !response.messages || response.messages.length === 0) {
            throw new Error('Invalid response format from Ollama API');
        }

        if (!response.messages[messageCount - 1].contents || response.messages[messageCount - 1].contents.length === 0) {
            throw new Error('Invalid response format from Ollama API');
        }

        return response.messages[messageCount - 1].contents[contentCount - 1].text;
    } catch (error) {
        console.error('Error parsing prompt response:', error);
        return null;
    }
}