import axios from "axios";

/**
 * @param method {string}
 * @param url {string}
 * @param body {any}
 * @param timeout {number|null}
 * @returns {Promise<axios.AxiosResponse<any>>}
 */
export async function sendRequest(method, url, body = null, timeout = 10000) {
    return await axios.request({
        method: method,
        url: url,
        data: body,
        timeout: timeout,
        withCredentials: true,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    });
}


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
