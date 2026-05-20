import { ref, type Ref } from "vue";
import Cookie from "js-cookie";

const AVAILABLE_VIEWS = [
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
] as const;

/**
 * Valid sidebar view identifiers.
 */
export type SidebarView = typeof AVAILABLE_VIEWS[number];

/**
 * This class handles manages the state of the sidebar in a responsive manner.
 */
export class SidebarManager {
    private static readonly _availableViews = AVAILABLE_VIEWS;

    private _selectedView: Ref<SidebarView>;
    private _isResizing: Ref<boolean>;

    /**
     * @param selectedView The initially selected view.
     */
    constructor(selectedView: SidebarView = 'none') {
        this._selectedView = ref(selectedView);
        this._isResizing = ref(false);

    }

    isValidView(key: string): key is SidebarView {
        return SidebarManager._availableViews.includes(key as SidebarView);
    }

    getSelectedView(): SidebarView {
        return this._selectedView.value;
    }

    /** select view, keep as-is if already open */
    selectView(key: SidebarView | string, collapsed: boolean = false): void {
        if (this.isValidView(key)) {
            if (this.viewNotInCollapsed(key) && collapsed) {
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
    toggleView(key: SidebarView): void {
        if (this.isViewSelected(key)) {
            this.selectView('none');
        } else {
            this.selectView(key);
        }
    }

    isViewSelected(key: SidebarView): boolean {
        return this.getSelectedView() === key;
    }

    isSidebarOpen(): boolean {
        return this.getSelectedView() !== 'none';
    }

    isResizing(): boolean {
        return this._isResizing.value;
    }

    setResizing(isResizing: boolean) {
        this._isResizing.value = isResizing;
    }

    close(): void {
        this.selectView('none');
    }

    viewNotInCollapsed(key: SidebarView): boolean {
        const restrictedViews: SidebarView[] = ['files', 'agents', 'extensions', 'mcp', 'config', 'debug'];
        return restrictedViews.includes(key);
    }
}

const sidebarManager = new SidebarManager();
export default sidebarManager;
