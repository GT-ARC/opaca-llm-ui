// names of the CSS-variables for individual colors
// theme-variants replace "color" with the name of the theme
import conf from "../config.js";
import {ref} from "vue";

const cssColors = [
    "background",
    "surface",
    "primary",
    "secondary",
    "accent",
    "text-primary",
    "text-secondary",
    "text-success",
    "text-danger",
    "border",
    "chat-user",
    "chat-ai",
    "input",
    "debug-console",
    "icon-invert",
];

// Color themes; if "basedOn" is null, the theme is defined directly in CSS
const colorThemes = {
    light: {
        "name": "Light",
        "basedOn": null,
    },
    dark: {
        "name": "Dark",
        "basedOn": null,
    },
    sscc: {
        "name": "Smart Space Control Centre",
        "basedOn": "light",
        "colors": {
            "background": "#eceff5",
            "surface": "#dae0eb",
            "primary": "#33cc99",
            "secondary": "#33cc99",
        },
    },
}

const currentTheme = ref(initColorTheme());

export function initColorTheme() {
    if (conf.ColorScheme === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark' : 'light';
    }
    return conf.ColorScheme;
}

export function getColorThemes() {
    return Object.fromEntries(
        Object.entries(colorThemes).map(([k,v]) => [k, v.name])
    );
}

export function setColorTheme(document, theme) {
    currentTheme.value = theme;
    for (const color of cssColors) {
        document.documentElement.style.setProperty(`--${color}-color`, getColor(theme, color));
    }
}

export function getCurrentTheme() {
    return currentTheme.value;
}

export function isDarkTheme(theme = null) {
    if (theme === null) return isDarkTheme(getCurrentTheme());
    if (theme === 'light') return false;
    if (theme === 'dark') return true;
    return isDarkTheme(colorThemes[theme].basedOn);
}

function getColor(theme, color) {
    if (colorThemes[theme].basedOn === null) {
        return `var(--${color}-${theme})`
    }
    if (color in colorThemes[theme].colors) {
        return colorThemes[theme].colors[color];
    }
    return getColor(colorThemes[theme].basedOn, color);
}
