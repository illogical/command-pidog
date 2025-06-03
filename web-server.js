let port = 5301;
let filename = "voice-recorder.html";

Bun.serve({
  port: port,
  fetch(request) {
    // Create response headers with CORS
    const headers = {
      "Access-Control-Allow-Origin": "*",  // Or specify your subdomains
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Content-Type": "text/html"
    };

    // Handle preflight requests
    if (request.method === "OPTIONS") {
      return new Response(null, { headers });
    }

    // Serve index.html for root path
    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "/" + filename) {
      return new Response(Bun.file("./" + filename), { headers });
    }
    
    // Fallback for other routes
    return new Response("Not Found", { 
      status: 404,
      headers: { "Content-Type": "text/plain" }
    });
  }
});

console.log("Listening on http://localhost:" + port);