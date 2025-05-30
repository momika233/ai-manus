import { ref, computed, onMounted, onUnmounted } from 'vue';
import { formatRelativeTime } from '../utils/time';

export function useRelativeTime(timestamp: number) {
  // Create a reactive current time variable to trigger re-rendering
  const currentTime = ref(Date.now());

  // Set a timer to update the time every minute
  let timer: number | null = null;

  onMounted(() => {
    timer = window.setInterval(() => {
      currentTime.value = Date.now();
    }, 60000); // Update every minute
  });

  onUnmounted(() => {
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  });

  // Calculate relative time, depends on currentTime for automatic updates
  const relativeTime = computed(() => {
    currentTime.value; // Depends on currentTime, recalculate when currentTime updates
    return formatRelativeTime(timestamp);
  });

  return {
    relativeTime
  };
} 