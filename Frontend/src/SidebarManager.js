
class SidebarManager {

    _availableViews = [
        'none',
        'connect',
        'questions',
        'agents',
        'config',
        'debug'
    ]

    constructor(selectedView = 'none') {
        this._selectedView = selectedView;
    }

    isValidView(key) {
        return this._availableViews.includes(key);
    }

    selectView(key) {
        if (this.isViewSelected(key)) {
            this._selectedView = 'none';
        }
        if (this.isValidView(key)) {
            this._selectedView = key;
        } else {
            this._selectedView = 'none';
        }
        this.$emit('on-sidebar-toggle',
            this._selectedView);
    }

    isViewSelected(key) {
        return this._selectedView === key;
    }

    isSidebarOpen() {
        return this._selectedView === 'none';
    }
}

const sidebarManager = new SidebarManager();
export default sidebarManager;
