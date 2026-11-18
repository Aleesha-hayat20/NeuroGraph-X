import { describe, expect, it } from 'vitest'
import { atlasLabel, formatCount, formatTime } from './format.js'

describe('format helpers', () => {
  it('names the four atlases and passes an unknown key through', () => {
    expect(atlasLabel('aal')).toBe('AAL')
    expect(atlasLabel('cc200')).toBe('CC200')
    expect(atlasLabel('ho')).toBe('Harvard-Oxford')
    expect(atlasLabel('dosenbach160')).toBe('Dosenbach 160')
    expect(atlasLabel('other')).toBe('other')
  })

  it('shows a UTC timestamp as date and time', () => {
    expect(formatTime('2026-11-17T14:39:21+00:00')).toBe('2026-11-17 14:39:21')
  })

  it('puts a thousands separator in counts', () => {
    expect(formatCount(1112)).toBe('1,112')
    expect(formatCount(861)).toBe('861')
  })
})