import {ref} from "vue";

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

    static minLevelByView = {
        files: 1,
        agents: 1,
        extensions: 1,
        mcp: 1,
        config: 1,
        debug: 1,
    };

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
    selectView(key, level= 1) {
        if (this.isValidView(key)) {
            if (this.isViewAllowedAtLevel(key, level)){
                this._selectedView.value = key;
            }
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

    isViewAllowedAtLevel(view, level) {
        const min = SidebarManager.minLevelByView[view];
        return min == null ? true : level >= min;
    }
}

const sidebarManager = new SidebarManager();
export default sidebarManager;
