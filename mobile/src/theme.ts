export type Colors = ReturnType<typeof palette>;

// Match the shared web palette. Green communicates successful results only.
export function palette(dark: boolean) {
  return dark
    ? { background: '#151518', surface: '#202024', text: '#F1F1F4', muted: '#B0B0BD', primary: '#A5B4FC', onPrimary: '#1B1740', selected: '#2B2C48', border: '#393940', danger: '#FFABB3', success: '#8ED5B2' }
    : { background: '#F7F7F9', surface: '#FFFFFF', text: '#202024', muted: '#62626E', primary: '#4F46E5', onPrimary: '#FFFFFF', selected: '#EEF2FF', border: '#E2E2E8', danger: '#B33D49', success: '#25634F' };
}
