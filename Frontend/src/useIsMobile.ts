import { ref, onMounted, onUnmounted, type Ref } from 'vue';

interface DeviceState {
    isMobile: Ref<boolean>;
    isTablet: Ref<boolean>;
    screenWidth: Ref<number>;
}

export function useDevice(): DeviceState {
    const isMobile = ref(window.innerWidth <= 768);
    const isTablet = ref(window.innerWidth > 768 && window.innerWidth <= 1024);
    const screenWidth = ref(window.innerWidth);

    const updateDevice = () => {
        screenWidth.value = window.innerWidth;
        isMobile.value = screenWidth.value <= 768;
        isTablet.value = screenWidth.value > 768 && screenWidth.value <= 1024;
    };

    onMounted(() => {
        window.addEventListener('resize', updateDevice);
    });

    onUnmounted(() => {
        window.removeEventListener('resize', updateDevice);
    });

    return { isMobile, isTablet, screenWidth };
}
