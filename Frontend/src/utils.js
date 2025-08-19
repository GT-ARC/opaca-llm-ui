import conf from '../config.js';

import axios from "axios";


class BackendClient {

    // OPACA connection

    async connect(url, user, pwd) {
        const body = {url: url, user: user, pwd: pwd};
        const res = await this.sendRequest("POST", "connect", body);
        return parseInt(res);
    }

    async disconnect() {
        await this.sendRequest("POST", "disconnect");
    }

    async getActions() {
        return await this.sendRequest("GET", "actions");
    }

    // chat

    async query(backend, user_query, store_in_history = true) {
        const body = {user_query: user_query, store_in_history: store_in_history};
        return await this.sendRequest("POST", `${backend}/query`, body);
    }
    
    // TODO query stream

    async stop() {
        await this.sendRequest("POST", "stop");
    }

    async history() {
        return await this.sendRequest("GET", "history");
    }

    async reset() {
        await this.sendRequest("POST", "reset");
    }

    async uploadFiles(files) {
        const formData = new FormData();
        for (const file of files) {
            formData.append("files", file);
        }
        // XXX extend sendRequest for this case?
        const response = await axios.post(`${conf.BackendAddress}/upload`, formData, {
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

    async getConfig(backend) {
        return await this.sendRequest('GET', `${backend}/config`);
    }

    async updateConfig(backend, config) {
        return await this.sendRequest('PUT', `${backend}/config`, config);
    }

    async resetConfig(backend) {
        return await this.sendRequest('POST', `${backend}/config/reset`);
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
 * 
 * @param {*} debugMessages list of existing debug messages (modified)
 * @param {*} text new message text
 * @param {*} type new message type 
 */
export function addDebugMessage(debugMessages, text, type) {
    if (! text) return;
    const message = {text: text, type: type};

    // if there are no messages yet, just push the new one
    if (debugMessages.length === 0) {
        debugMessages.push(message);
    } else {
        const lastMessage = debugMessages[debugMessages.length - 1];
        if (lastMessage.type === type) {
            // if the type is the same, the new message is a continuation of the last message
            if (/^Tool \d+/.test(text)) {
                lastMessage.text = text;  // replace
            } else {
                lastMessage.text += text; // append
            }
        } else {
            // new message type
            debugMessages.push(message);
        }
    }
}
