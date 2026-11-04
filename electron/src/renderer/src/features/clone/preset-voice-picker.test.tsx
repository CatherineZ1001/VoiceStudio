import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import '@/i18n';
import i18next from 'i18next';
import { PresetVoicePicker, presetVoiceLabel } from './preset-voice-picker';
const state = vi.hoisted(() => ({
  presets: undefined as string[] | undefined,
  saved: '',
}));
vi.mock('@/hooks/use-engines', () => ({
  useEngines: () => ({ activeTts: { voice_presets: state.presets } }),
}));
vi.mock('@/lib/store/clone-settings', () => ({
  useCloneSetting: () => state.saved,
  setCloneSetting: vi.fn(),
}));

it('renders nothing for an engine without presets (#2938)', () => {
  state.presets = [];
  const { container } = render(<PresetVoicePicker />);
  expect(container).toBeEmptyDOMElement();
  state.presets = undefined;
  render(<PresetVoicePicker />);
  expect(screen.queryByRole('combobox', { name: 'Preset voice' })).toBeNull();
});

it('shows the default preset until the user picks one, then the saved one', () => {
  state.presets = ['M1', 'M3', 'F3'];
  state.saved = '';
  const view = render(<PresetVoicePicker />);
  expect(screen.getByRole('combobox', { name: 'Preset voice' })).toHaveTextContent('Male 1');
  state.saved = 'F3';
  view.rerender(<PresetVoicePicker />);
  expect(screen.getByRole('combobox', { name: 'Preset voice' })).toHaveTextContent('Female 3');
});

it('labels speaker ids readably and leaves unknown ids alone', () => {
  const t = i18next.t.bind(i18next);
  expect(presetVoiceLabel('M4', t)).toBe('Male 4');
  expect(presetVoiceLabel('F5', t)).toBe('Female 5');
  expect(presetVoiceLabel('narrator', t)).toBe('narrator');
});
