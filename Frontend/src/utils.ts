// @ts-ignore
import conf from '../config.js';
import axios, { type  Method } from "axios";
import type { 
    Container, 
    PostContainerRequest, 
    PostContainerResponse,
    ContainerExtraPorts, 
    InvokeResponse, 
    QueryResponse, 
    Chat, 
    SearchResult, 
    OpacaFile, 
    ConfigPayload, 
    SessionPrompts,
    PushMessage
} from "./models";

class BackendClient {
    // OPACA connection

    async connect(url: string, user: string, pwd: string): Promise<number> {
        const body = {url: url, user: user, pwd: pwd};
        const res = await this.sendRequest("POST", "connect", body);
        return parseInt(res);
    }

    async getConnection(): Promise<string | null> {
        return this.sendRequest("GET", "connection");
    }

    async disconnect(): Promise<void> {
        await this.sendRequest("POST", "disconnect");
    }

    async getContainers(): Promise<Container[]> {
        return this.sendRequest("GET", "containers");
    }

    async deployContainer(postContainer: PostContainerRequest, update: boolean = false): Promise<PostContainerResponse> {
        return this.sendRequest("POST", `containers?update=${update}`, postContainer);
    }

    async undeployContainer(containerId: string): Promise<void> {
        return this.sendRequest("DELETE", `containers/${containerId}`);
    }

    async invokeAction(agent: string, action: string, parameters: any): Promise<InvokeResponse> {
        const body = { agent, action, parameters };
        return this.sendRequest("POST", "invoke", body);
    }

    async getExtraPorts(): Promise<ContainerExtraPorts[]> {
        return this.sendRequest("GET", "extra-ports");
    }

    async getPlatformInfo(lang: string): Promise<string> {
        return this.sendRequest("POST", `platform-info?lang=${lang}`, null, 60000);
    }

    // chat

    async query(chatId: string, method: string, userQuery: string, streaming: boolean = false, timeout: number = 10000): Promise<QueryResponse> {
        const body = { user_query: userQuery, streaming };
        return await this.sendRequest("POST", `chats/${chatId}/query/${method}`, body, timeout);
    }

    async queryNoChat(method: string, userQuery: string, timeout: number = 10000): Promise<QueryResponse> {
        const body = { user_query: userQuery };
        return await this.sendRequest("POST", `query/${method}`, body, timeout);
    }

    // TODO query stream

    async stop(): Promise<void> {
        await this.sendRequest("POST", `stop`);
    }

    async chats(): Promise<Chat[]> {
        return await this.sendRequest("GET", "chats");
    }

    async history(chatId: string): Promise<Chat> {
        return await this.sendRequest("GET", `chats/${chatId}`);
    }

    async delete(chatId: string): Promise<void> {
        await this.sendRequest("DELETE", `chats/${chatId}`);
    }

    async updateName(chatId: string, newName: string): Promise<void> {
        await this.sendRequest("PUT", `chats/${chatId}?new_name=${newName}`);
    }

    async deleteAllChats(): Promise<void> {
        await this.sendRequest("DELETE", `chats`);
    }

    async search(query: string): Promise<Record<string, SearchResult[]>> {
        return await this.sendRequest("POST", `chats/search?query=${query}`);
    }

    async append(chatId: string, pushMessage: PushMessage, autoAppend: boolean): Promise<any> {
        // Reset query
        pushMessage.query = "";
        return await this.sendRequest("POST", `chats/${chatId}/append?auto_append=${autoAppend}`, pushMessage);
    }

    // files

    async files(): Promise<Record<string, OpacaFile>> {
        return await this.sendRequest("GET", "files");
    }

    async deleteFile(fileId: string, ignoreError: boolean): Promise<boolean> {
        return await this.sendRequest("DELETE", `files/${fileId}?ignore_error=${ignoreError}`);
    }

    async suspendFile(fileId: string, suspend: boolean): Promise<void> {
        await this.sendRequest("PATCH", `files/${fileId}?suspend=${suspend}`);
    }

    async renameFile(fileId: string, name: string): Promise<void> {
        await this.sendRequest("PATCH", `files/${fileId}?name=${name}`);
    }

    async uploadFiles(files: File[]): Promise<{ uploadedFiles: OpacaFile[] }> {
        const formData = new FormData();
        for (const file of files) {
            formData.append("files", file);
        }
        // XXX extend sendRequest for this case?
        const response = await axios.post(`${conf.BackendAddress}/files`, formData, {
            timeout: 10000,
            withCredentials: true,
            headers: {
                'Content-Type': 'multipart/form-data',
                'Access-Control-Allow-Origin': '*'
            }
        }).catch((error: any) => {
            console.error('Upload failed:', error);
            throw new Error(error.toJSON());
        });
        return response.data;
    }

    // config

    async getConfig(method: string): Promise<ConfigPayload> {
        return await this.sendRequest('GET', `config/${method}`);
    }

    async updateConfig(method: string, config: any): Promise<ConfigPayload> {
        return await this.sendRequest('PUT', `config/${method}`, config);
    }

    async resetConfig(method: string): Promise<ConfigPayload> {
        return await this.sendRequest('DELETE', `config/${method}`);
    }

    // prompts

    async getPrompts(): Promise<SessionPrompts> {
        return await this.sendRequest("GET", "prompts");
    }

    async savePrompts(prompts: SessionPrompts): Promise<void> {
        return await this.sendRequest("POST", "prompts", prompts);
    }

    async resetPrompts(): Promise<void> {
        return await this.sendRequest("DELETE", "prompts");
    }

    // mcp

    async getMCPs(): Promise<Record<string, any>> {
        return await this.sendRequest("GET", "mcp");
    }

    async addMcp(mcp: any): Promise<void> {
        return await this.sendRequest("POST", "mcp", mcp);
    }

    async deleteMcp(serverLabel: string): Promise<void> {
        return await this.sendRequest("DELETE", `mcp/${serverLabel}`);
    }

    // internal helper

    async sendRequest(method: Method | string, path: string, body: any = null, timeout: number = 10000): Promise<any> {
        const response = await axios.request({
            method: method as Method,
            url: `${conf.BackendAddress}/${path}`,
            data: body,
            timeout: timeout,
            withCredentials: true,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        });
        return response.data;
    }

}

const backendClient = new BackendClient();
export default backendClient;


// randomly shuffle array in-place
export function shuffleArray<T>(array: T[]): void {
    let currentIndex = array.length;
    while (currentIndex !== 0) {
        let randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex--;
        [array[currentIndex], array[randomIndex]] = [
            array[randomIndex], array[currentIndex]];
    }
}

export function isSecureConnection(): boolean {
    return window.location.protocol === 'https'
        || window.location.hostname === 'localhost'
        || window.location.hostname === '127.0.0.1';
}

export interface DebugMessage {
    id: string;
    type?: string;
    text?: string;
    chatId?: string;
    [key: string]: any;
}

/**
 * Add debug message to list of debug-messages. Depending on the type and content, the
 * message may be added as a new message, or extend or replace the last received message.
 * @param {Array} debugMessages list of existing debug messages (modified)
 * @param {object} message new message object with fields {id, type, text, chatId}
 */
export function addDebugMessage(debugMessages: DebugMessage[], message: DebugMessage): void {
    if (! message || ! message.text) return;
    // find debug message with the same ID, if any
    const matchingMessage = debugMessages.find( (m) => m.id === message.id);
    if (message.id != null && matchingMessage != null) {
        // append to existing message
        matchingMessage.text += message.text;
    } else {
        // add copy of new message
        debugMessages.push(structuredClone(message));
    }
}

/**
 * Replace an existing debug message with the same ID, or add it if missing.
 * @param {Array} debugMessages list of existing debug messages (modified)
 * @param {object} message new message object with fields {id, type, text, chatId}
 */
export function replaceDebugMessage(debugMessages: DebugMessage[], message: DebugMessage): void {
    if (! message || ! message.text) return;
    const matchingIndex = debugMessages.findIndex( (m) => m.id === message.id);
    if (message.id != null && matchingIndex >= 0) {
        debugMessages.splice(matchingIndex, 1, structuredClone(message));
    } else {
        debugMessages.push(structuredClone(message));
    }
}

/**
 * Format tool results for debug output.
 * Objects and arrays are pretty-printed, primitives stay compact.
 * @param {*} result
 * @returns {string}
 */
export function formatToolDebugResult(result: any): string {
    if (result === undefined) return "undefined";
    if (typeof result === "object") {
        return JSON.stringify(result, null, 2);
    }
    return JSON.stringify(result);
}

/**
 * Prefer structured agent output for debug rendering when available.
 * @param {object} agentMessage
 * @returns {string}
 */
export function formatAgentDebugText(agentMessage: any): string {
    if (!agentMessage) return "";
    if (agentMessage.formatted_output != null) {
        return formatToolDebugResult(agentMessage.formatted_output);
    }
    if (typeof agentMessage.content !== "string") {
        return agentMessage.content == null ? "" : formatToolDebugResult(agentMessage.content);
    }

    const trimmed = agentMessage.content.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}"))
        || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
        try {
            return formatToolDebugResult(JSON.parse(trimmed));
        } catch {
            // Keep the original text when it only looks like JSON.
        }
    }

    return agentMessage.content;
}
