// The studio's fixed motion-brand constants (motion-playbook.md §1). Do not restyle
// per video — pick components and feed data; the look stays locked.
export const BRAND = {
  navyIn: '#15314a',
  navyMid: '#0d1428',
  navyOut: '#090d1c',
  red: '#ff4d4d',
  green: '#3ddc84',
  white: '#f5f7ff',
  // Hand-drawn caution ink for annotations and figure marks (2026-09-24). Paper worlds
  // deepen it at the call site, as they do red.
  amber: '#ffb020',
  font: '-apple-system, "Helvetica Neue", Arial, sans-serif',
};

// the house entrance easing (motion-playbook §1)
export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
