# Command Pidog: Voice Command Web App with Tailscale

This project provides a secure, private web interface for voice commands using a local Whisper server, accessible via your Tailscale network.

## Quick Start

1. **Set up your Tailscale Auth Key**

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
- The web app expects a Whisper server at the endpoint configured in `command-pidog.json` (default: `http://localhost:5000/transcribe`).

## Stopping

```
docker compose down
```