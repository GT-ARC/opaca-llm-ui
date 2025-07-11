// themes defined directly in CSS
export const baseThemes = [
    "light",
    "dark",
]

// names of the CSS-variables for individual colors
// theme-variants replace "color" with the name of the theme
export const cssColors = [
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

// derived color themes
export const colorThemes = {
    sscc: {
        "basedOn": "light",
        "colors": {

        },
    },
}

export function setColorTheme(document, theme) {
    for (const color of cssColors) {
        document.documentElement.style.setProperty(`--${color}-color`, getColor(theme, color));
    }
}

function getColor(theme, color) {
    if (baseThemes.includes(theme)) {
        return `var(--${color}-${theme})`
    }
    if (colorThemes[theme].colors.includes(color)) {
        return colorThemes[theme].colors[color];
    }
    return getColor(colorThemes[theme].basedOn, color);
}
