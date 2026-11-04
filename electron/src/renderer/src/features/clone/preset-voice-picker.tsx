import { UserRoundIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useEngines } from '@/hooks/use-engines';
import { setCloneSetting, useCloneSetting } from '@/lib/store/clone-settings';

/** "M3" → "Male 3", "F4" → "Female 4"; any other id is shown as-is. */
export function presetVoiceLabel(id: string, t: TFunction): string {
  const match = /^([MF])(\d+)$/.exec(id);
  if (!match) return id;
  return t(match[1] === 'M' ? 'clone.preset_voice_male' : 'clone.preset_voice_female', {
    n: match[2],
  });
}

/**
 * Built-in speaker picker for engines that ship presets (#2938). Renders
 * nothing for every other engine, so it never shows a control that does
 * nothing. The first preset is the engine's default voice.
 */
export function PresetVoicePicker({ disabled = false }: { disabled?: boolean }) {
  const { t } = useTranslation();
  const { activeTts } = useEngines();
  const saved = useCloneSetting('presetVoice');
  const presets = activeTts?.voice_presets ?? [];
  if (presets.length === 0) return null;
  const value = presets.includes(saved) ? saved : presets[0];
  const items = presets.map((id) => ({ value: id, label: presetVoiceLabel(id, t) }));
  return (
    <Select
      items={items}
      value={value}
      disabled={disabled}
      onValueChange={(next) => typeof next === 'string' && setCloneSetting('presetVoice', next)}
    >
      <SelectTrigger
        className="h-9 border-transparent bg-transparent px-2.5 dark:bg-transparent"
        aria-label={t('clone.preset_voice')}
      >
        <UserRoundIcon className="text-muted-foreground" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
