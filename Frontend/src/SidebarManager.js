import {ref} from "vue";
import Cookie from "js-cookie";

/**
 * This class handles manages the state of the sidebar in a responsive manner.
 */
class SidebarManager {

    static _availableViews = [
        'none',
        'info',
        'chats',
        'files',
        'questions',
        'agents',
        'extensions',
        'mcp',
        'config',
        'debug',
        'faq',
    ]

    /**
     * @param selectedView {string} The initially selected view.
     */
    constructor(selectedView = 'none') {
        this._selectedView = ref(selectedView);
    }

    isValidView(key) {
        return SidebarManager._availableViews.includes(key);
    }

    getSelectedView() {
        return this._selectedView.value;
    }

    /** select view, keep as-is if already open */
    selectView(key, collapsed = false) {
        if (this.isValidView(key)) {
            if (this.viewNotInCollapsed(key) && collapsed){
                return;
            }
            this._selectedView.value = key;
            Cookie.set('selected_view', key);
        } else {
            console.warn(`${key} is not a valid sidebar view`);
            this._selectedView.value = 'none';
        }
    }

    /** select if not already open, close otherwise */
    toggleView(key) {
        if (this.isViewSelected(key)) {
            this.selectView('none');
        } else {
            this.selectView(key);
        }
    }

    isViewSelected(key) {
        return this.getSelectedView() === key;
    }

    isSidebarOpen() {
        return this.getSelectedView() !== 'none';
    }

    close() {
        this.selectView('none');
    }

    viewNotInCollapsed(key) {
        return ['files', 'agents', 'extensions', 'mcp', 'config', 'debug'].includes(key);
    }
}

const sidebarManager = new SidebarManager();
export default sidebarManager;
