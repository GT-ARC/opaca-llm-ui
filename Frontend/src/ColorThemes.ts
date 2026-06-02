// names of the CSS-variables for individual colors
// theme-variants replace "color" with the name of the theme
import conf from "../config";
import { ref, type Ref } from "vue";

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
] as const;

type CssColor = typeof cssColors[number];

interface ColorTheme {
    name: string;
    basedOn: string | null;
    colors?: Partial<Record<CssColor, string>>;
}

// Color themes; if "basedOn" is null, the theme is defined directly in CSS
const colorThemes: Record<string, ColorTheme> = {
    system: {
        "name": "Adaptive",
        "basedOn": null,
    },
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
};

const currentTheme: Ref<string> = ref(conf.colorScheme);

function getEffectiveColorTheme(): string {
    if (conf.colorScheme === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark' : 'light';
    }
    return conf.colorScheme;
}

export function getColorThemes(): Record<string, string> {
    return Object.fromEntries(
        Object.entries(colorThemes).map(([k,v]) => [k, v.name])
    );
}

export function setColorTheme(theme: string): void {
    conf.colorScheme = theme;
    currentTheme.value = getEffectiveColorTheme();
    for (const color of cssColors) {
        document.documentElement.style.setProperty(`--${color}-color`, getColor(currentTheme.value, color));
    }
}

export function getCurrentTheme(): string {
    return currentTheme.value;
}

export function isDarkTheme(theme: string | null = null): boolean {
    if (theme === null) return isDarkTheme(getCurrentTheme());
    if (theme === 'light') return false;
    if (theme === 'dark') return true;
    return isDarkTheme(colorThemes[theme].basedOn);
}

/**
 * Recursively get the color value for the given theme and color name.
 */
function getColor(theme: string, color: CssColor): string {
    const themeConfig = colorThemes[theme];

    // If theme doesn't exist, fallback to light/CSS var logic
    if (!themeConfig) return `var(--${color}-light)`;

    // If it's a base theme (no parent), return the standard CSS variable reference
    if (themeConfig.basedOn === null) {
        return `var(--${color}-${theme})`;
    }

    // If the color is explicitly defined in this theme's overrides
    if (themeConfig.colors && color in themeConfig.colors) {
        return themeConfig.colors[color]!;
    }

    // Otherwise, recurse up to the parent theme
    return getColor(themeConfig.basedOn, color);
}
