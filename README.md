# Command Pidog: Voice Command Web App with Tailscale

This project provides a secure, private web interface for voice commands using a local Whisper server, with optional queue functionality, accessible via your Tailscale network.

## Quick Start

1. **Set up your configuration**

   - Create a `config.json` file in the project root with the following structure:
     ```json
     {
       "TRANSCRIBE_ENDPOINT": "https://localhost:5000/transcribe",
       "QUEUE_URL": "https://your-queue-server/queue/add/{queue-name}",
       "CHAT_URL": "https://your-chat-server/chat"
     }
     ```
     - `TRANSCRIBE_ENDPOINT`: The URL of your Whisper server's transcription endpoint
     - `QUEUE_URL`: The base URL of your queue server to send commands to the Pidog.
     - `CHAT_URL`: The URL of your chat server to prompt to get back Pidog commands based upon the transcription.
     

   - Set up your Tailscale Auth Key:

     - Obtain a Tailscale [auth key](https://login.tailscale.com/admin/settings/keys).
     - Create a `.env` file in this directory with:
       ```
       TS_AUTHKEY=tskey-xxxxxxxxxxxxxxxx
       ```

2. **Start the stack**

   ```
   docker compose up -d
   ```

   This will start:
   - `tailscale`: Connects to your Tailscale network.
   - `bun-web`: Serves the voice command web app, accessible via your Tailscale IP.

3. **Check Tailscale status**

   ```
   docker exec -it ts-command-pidog tailscale status
   ```

   To see HTTPS serve status:
   ```
   docker exec -it ts-command-pidog tailscale serve status
   ```

4. **Access the Web App**

   - Find your container's Tailscale IP:
     ```
     docker exec -it ts-command-pidog tailscale ip -4
     ```
   - Open `http://<tailscale-ip>/` in your browser (from any device on your Tailscale network).

## Notes

- The web app files are in `voice-commands/`.
- The Bun server serves static files from this directory.
- The web app expects a Whisper server at the endpoint configured in `config.json`.
- The queue functionality allows voice commands to be sent to a message queue for asynchronous processing. This is useful for integrating with other services or handling long-running commands.

## Queue Integration

The application includes queue functionality that can be used to process voice commands asynchronously. To use this feature:

1. Set the `QUEUE_URL` in your `config.json` to point to your queue server
2. The application will POST messages to `{QUEUE_URL}/{queueName}` with the following format:
   ```json
   {
     "message": "transcribed text from voice command"
   }
   ```

## Stopping

```
docker compose down
```