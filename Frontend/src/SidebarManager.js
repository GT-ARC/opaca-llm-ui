import {ref} from "vue";

class SidebarManager {

    static _availableViews = [
        'none',
        'connect',
        'questions',
        'agents',
        'config',
        'debug'
    ]

    constructor(sidebarElement, selectedView = 'none') {
        this._element = document.getElementById(sidebarElement);
        this._selectedView = ref(selectedView);
    }

    isValidView(key) {
        return SidebarManager._availableViews.includes(key);
    }

    getSelectedView() {
        return this._selectedView.value;
    }

    setSelectedView(key) {
        this._selectedView.value = value;
    }

    selectView(key) {
        if (this.isValidView(key)) {
            this.setSelectedView(key);
        } else {
            this.setSelectedView('none');
        }
    }

    selectViewOrClose(key) {
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
        return this.getSelectedView() === 'none';
    }

    emitOnChange() {
        this.$emit('on-sidebar-toggle', this.getSelectedView());
    }
}

const sidebarManager = new SidebarManager();
export default sidebarManager;
