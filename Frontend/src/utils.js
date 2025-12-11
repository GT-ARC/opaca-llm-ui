import conf from '../config.js';

import axios from "axios";


class BackendClient {

    // OPACA connection

    async connect(url, user, pwd) {
        const body = {url: url, user: user, pwd: pwd};
        const res = await this.sendRequest("POST", "connect", body);
        return parseInt(res);
    }

    async getConnection() {
        return await this.sendRequest("GET", "connection");
    }

    async disconnect() {
        await this.sendRequest("POST", "disconnect");
    }

    async getActions() {
        return await this.sendRequest("GET", "actions");
    }

    async getExtraPorts() {
        return await this.sendRequest("GET", "extra-ports");
    }

    // chat

    async query(chatId, method, user_query, streaming=False, timeout=10000) {
        const body = {user_query: user_query, streaming: streaming};
        return await this.sendRequest("POST", `chats/${chatId}/query/${method}`, body, timeout);
    }

    async queryNoChat(method, user_query) {
        const body = {user_query: user_query};
        return await this.sendRequest("POST", `query/${method}`, body);
    }

    // TODO query stream

    async stop() {
        await this.sendRequest("POST", `stop`);
    }

    async chats() {
        return await this.sendRequest("GET", "chats");
    }

    async history(chatId) {
        return await this.sendRequest("GET", `chats/${chatId}`);
    }

    async delete(chatId) {
        await this.sendRequest("DELETE", `chats/${chatId}`);
    }

    async updateName(chatId, newName) {
        await this.sendRequest("PUT", `chats/${chatId}?new_name=${newName}`);
    }

    async deleteAllChats() {
        await this.sendRequest("DELETE", `chats`);
    }

    async search(query) {
        return await this.sendRequest("POST", `chats/search?query=${query}`);
    }

    async append(chatId, pushMessage, autoAppend) {
        // Reset query
        pushMessage.query = "";
        return await this.sendRequest("POST", `chats/${chatId}/append?auto_append=${autoAppend}`, pushMessage);
    }

    // files

    async files() {
        return await this.sendRequest("GET", "files");
    }

    async deleteFile(file_id) {
        await this.sendRequest("DELETE", `files/${file_id}`);
    }

    async suspendFile(file_id, suspend) {
        await this.sendRequest("PATCH", `files/${file_id}?suspend=${suspend}`);
    }

    async uploadFiles(files) {
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
        }).catch(error => {
            console.error('Upload failed:', error);
            throw new Error(error.toJSON());
        });
        return response.data;
    }

    // config

    async getConfig(method) {
        return await this.sendRequest('GET', `config/${method}`);
    }

    async updateConfig(method, config) {
        return await this.sendRequest('PUT', `config/${method}`, config);
    }

    async resetConfig(method) {
        return await this.sendRequest('DELETE', `config/${method}`);
    }

    // bookmarks

    async getBookmarks() {
        return await this.sendRequest("GET", "bookmarks");
    }

    async saveBookmarks(bookmarks) {
        return await this.sendRequest("POST", "bookmarks", bookmarks);
    }

    // mcp

    async getMCPs() {
        return await this.sendRequest("GET", "mcp");
    }

    async addMcp(mcp) {
        return await this.sendRequest("POST", "mcp", mcp);
    }

    async deleteMcp(mcp_name) {
        return await this.sendRequest("DELETE", `mcp/`, mcp_name);
    }

    // internal helper

    async sendRequest(method, path, body = null, timeout = 10000) {
        const response = await axios.request({
            method: method,
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
export function shuffleArray(array) {
    let currentIndex = array.length;
    while (currentIndex !== 0) {
        let randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex--;
        [array[currentIndex], array[randomIndex]] = [
            array[randomIndex], array[currentIndex]];
    }
}

/**
 * Add debug message to list of debug-messages. Depending on the type and content, the
 * message may be added as a new message, or extend or replace the last received message.
 * @param {Array} debugMessages list of existing debug messages (modified)
 * @param {object} message new message object with fields {id, type, text, chatId}
 */
export function addDebugMessage(debugMessages, message) {
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
