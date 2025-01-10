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