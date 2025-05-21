let port = 5301;
let filename = "voice-recorder.html";

Bun.serve({
  port: port,
  fetch(request) {
    // Serve index.html for root path
    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "/" + filename) {
      return new Response(Bun.file("./" + filename), {
        headers: { "Content-Type": "text/html" }
      });
    }
    // Fallback for other routes
    return new Response("Not Found", { status: 404 });
  }
});

console.log("Listening on http://localhost:" + port);