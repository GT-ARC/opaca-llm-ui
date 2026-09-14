let oauthWindow: Window | null = null;

/** Reserve a popup synchronously from the add-dialog click event. */
export function prepareMcpOAuthWindow(): void {
    oauthWindow = window.open("about:blank", "sage-mcp-oauth", "popup,width=720,height=800");
    if (oauthWindow) {
        oauthWindow.opener = null;
        oauthWindow.document.title = "MCP Authorization";
        oauthWindow.document.body.textContent = "Checking MCP authentication...";
    }
}

export function showMcpAuthorization(authorizationUrl: string): void {
    if (oauthWindow && !oauthWindow.closed) {
        oauthWindow.location.href = authorizationUrl;
    } else {
        oauthWindow = window.open(authorizationUrl, "sage-mcp-oauth", "popup,width=720,height=800");
        if (oauthWindow) oauthWindow.opener = null;
    }
}

export function closeMcpOAuthWindow(): void {
    if (oauthWindow && !oauthWindow.closed) oauthWindow.close();
    oauthWindow = null;
}
