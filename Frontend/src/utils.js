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

    async search(query) {
        return await this.sendRequest("POST", `chats/search?query=${query}`);
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
    message = structuredClone(message); // since it may be modified later

    // if there are no messages yet, just push the new one
    if (debugMessages.length === 0) {
        debugMessages.push(message);
    } else {
        const lastMessage = debugMessages[debugMessages.length - 1];
        if (message.id != null && lastMessage.id === message.id) {
            if (/^Tool \d+/.test(message.text)) {
                lastMessage.text = message.text;  // replace
            } else {
                lastMessage.text += message.text; // append
            }
        } else {
            // new message type
            debugMessages.push(message);
        }
    }
}
