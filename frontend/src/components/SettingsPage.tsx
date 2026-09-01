import { useEffect, useMemo, useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowLeft, faCheck, faEye, faEyeSlash, faGear, faKey,
  faMicrophone, faVolumeHigh, faBolt, faUser, faAtom, faSliders,
} from '@fortawesome/free-solid-svg-icons';
import { faGoogle } from '@fortawesome/free-brands-svg-icons';
import '../styles/settings.css';

const WS_URL = import.meta.env.VITE_EVA_WS_URL || `ws://${window.location.hostname || '127.0.0.1'}:8765`;
const VOICES = ['Charon', 'Puck', 'Aoede', 'Kore', 'Fenrir', 'Leda', 'Orus', 'Zephyr'];
const SECRET_MASK = '••••';

type GoogleAccount = { connected: boolean; email: string | null; picture?: string | null };
type Settings = {
  gemini_api_key: string; youtube_api_key: string; youtube_channel_handle: string;
  voice: string; sfx_enabled: boolean; sfx_volume: number; proactive_enabled: boolean;
  language: string; wake_listener_enabled: boolean; auto_start: boolean; google_account: GoogleAccount;
  user_name: string; address_style: string; response_length: string; humor_level: number;
  proactivity_level: number; voice_tone: string; persona_prompt: string;
  voice_volume: number; speech_speed: number; interrupt_enabled: boolean; auto_duck_music: boolean; fallback_voice: string;
  sfx_startup_enabled: boolean; sfx_listening_enabled: boolean; sfx_thinking_enabled: boolean;
  sfx_success_enabled: boolean; sfx_error_enabled: boolean; sfx_notification_enabled: boolean;
  sfx_startup_volume: number; sfx_listening_volume: number; sfx_thinking_volume: number;
  sfx_success_volume: number; sfx_error_volume: number; sfx_notification_volume: number;
  orb_style: string; particle_density: number; particle_speed: number; glow_intensity: number;
  orb_listening_color: string; orb_speaking_color: string; orb_thinking_color: string; orb_muted_color: string;
  particle_animation_enabled: boolean; glow_enabled: boolean; pulse_enabled: boolean; audio_reactive_enabled: boolean;
};

const defaults: Settings = {
  gemini_api_key: '', youtube_api_key: '', youtube_channel_handle: '', voice: 'Charon', sfx_enabled: true, sfx_volume: 20,
  proactive_enabled: true, language: 'az-AZ', wake_listener_enabled: true, auto_start: false,
  google_account: { connected: false, email: null, picture: null }, user_name: 'Abdulla', address_style: 'Abdulla',
  response_length: 'normal', humor_level: 30, proactivity_level: 50, voice_tone: 'balanced', persona_prompt: '',
  voice_volume: 100, speech_speed: 1, interrupt_enabled: true, auto_duck_music: true, fallback_voice: '',
  sfx_startup_enabled: true, sfx_listening_enabled: true, sfx_thinking_enabled: true, sfx_success_enabled: true,
  sfx_error_enabled: true, sfx_notification_enabled: true, sfx_startup_volume: 100, sfx_listening_volume: 100,
  sfx_thinking_volume: 100, sfx_success_volume: 100, sfx_error_volume: 100, sfx_notification_volume: 100,
  orb_style: 'default', particle_density: 100, particle_speed: 100, glow_intensity: 100,
  orb_listening_color: '0, 255, 136', orb_speaking_color: '68, 136, 255', orb_thinking_color: '255, 204, 0', orb_muted_color: '200, 30, 80',
  particle_animation_enabled: true, glow_enabled: true, pulse_enabled: true, audio_reactive_enabled: true,
};

function Toggle({ value, onChange }: { value: boolean; onChange: () => void }) {
  return <button type="button" className={`toggle ${value ? 'on' : ''}`} onClick={onChange}><span /></button>;
}

function Range({ label, value, min = 0, max = 100, step = 1, onChange }: { label: string; value: number; min?: number; max?: number; step?: number; onChange: (value: number) => void }) {
  return <label className="settings-range"><div><span>{label}</span><strong>{value}</strong></div><input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(Number(e.target.value))} /></label>;
}

function SettingsPage({ onClose }: { onClose: () => void }) {
  const [settings, setSettings] = useState<Settings>(defaults);
  const [showGemini, setShowGemini] = useState(false), [showYoutube, setShowYoutube] = useState(false);
  const [status, setStatus] = useState(''), [saving, setSaving] = useState(false), [googleBusy, setGoogleBusy] = useState(false);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    socket.onopen = () => socket.send(JSON.stringify({ type: 'settings.get' }));
    socket.onmessage = message => { try { const event = JSON.parse(message.data); if (event.type === 'settings.state') setSettings({ ...defaults, ...event.settings, google_account: { ...defaults.google_account, ...(event.settings.google_account || {}) } }); } catch { /* Ignore malformed bridge messages. */ } };
    return () => socket.close();
  }, []);

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => { setSettings(current => ({ ...current, [key]: value })); setStatus(''); };
  const clearSecretForEdit = (key: 'gemini_api_key' | 'youtube_api_key') => { if (settings[key].startsWith(SECRET_MASK)) update(key, ''); };

  const googleAction = (type: 'google.connect' | 'google.disconnect') => {
    setGoogleBusy(true); setStatus(type === 'google.connect' ? 'GOOGLE GİRİŞİ GÖZLƏNİLİR...' : 'GOOGLE HESABI AYRILIR...');
    const socket = new WebSocket(WS_URL); socket.onopen = () => socket.send(JSON.stringify({ type }));
    socket.onmessage = message => { try { const event = JSON.parse(message.data); if (event.type === 'google.account') { update('google_account', event.account); setStatus(event.account?.connected ? 'GOOGLE HESABI QOŞULDU' : 'GOOGLE HESABI AYRILDI'); setGoogleBusy(false); socket.close(); } else if (event.type === 'bridge.error') { setStatus(event.message || 'GOOGLE ƏMƏLİYYATI UĞURSUZ OLDU'); setGoogleBusy(false); socket.close(); } } catch { setStatus('GOOGLE ƏMƏLİYYATI UĞURSUZ OLDU'); setGoogleBusy(false); socket.close(); } };
    socket.onerror = () => { setStatus('E.V.A RUNTIME BAĞLANTISI YOXDUR'); setGoogleBusy(false); };
  };

  const save = () => {
    setSaving(true); setStatus('YADDA SAXLANIR...'); const socket = new WebSocket(WS_URL);
    socket.onopen = () => socket.send(JSON.stringify({ type: 'settings.update', settings }));
    socket.onmessage = message => { try { const event = JSON.parse(message.data); if (event.type === 'settings.saved') { setSettings(current => ({ ...current, ...event.settings })); setStatus('PARAMETRLƏR YADDA SAXLANILDI'); setSaving(false); socket.close(); } if (event.type === 'bridge.error') { setStatus(event.message || 'SAXLAMA XƏTASI'); setSaving(false); socket.close(); } } catch { setStatus('SAXLAMA XƏTASI'); setSaving(false); socket.close(); } };
    socket.onerror = () => { setStatus('E.V.A RUNTIME BAĞLANTISI YOXDUR'); setSaving(false); };
  };

  const sfxLabel = useMemo(() => `${settings.sfx_volume}%`, [settings.sfx_volume]);
  const sfxItems: Array<[string, keyof Settings, keyof Settings]> = [
    ['Startup', 'sfx_startup_enabled', 'sfx_startup_volume'], ['Listening', 'sfx_listening_enabled', 'sfx_listening_volume'],
    ['Thinking', 'sfx_thinking_enabled', 'sfx_thinking_volume'], ['Success', 'sfx_success_enabled', 'sfx_success_volume'],
    ['Error', 'sfx_error_enabled', 'sfx_error_volume'], ['Notification', 'sfx_notification_enabled', 'sfx_notification_volume'],
  ];

  return <div className="settings-screen">
    <div className="settings-grid-bg" />
    <header className="settings-header"><button className="settings-back" onClick={onClose} aria-label="Geri"><FontAwesomeIcon icon={faArrowLeft} /></button><div><span className="settings-eyebrow">E.V.A / CONFIGURATION</span><h1>PARAMETRLƏR</h1><p>EVA-nın davranışını, səsini və görünüşünü idarə et.</p></div><div className="settings-header-icon"><FontAwesomeIcon icon={faGear} /></div></header>
    <main className="settings-content">
      <section className="settings-section"><div className="settings-section-title"><FontAwesomeIcon icon={faUser} /><span>EVA PERSONA</span><small>IDENTITY</small></div>
        <div className="settings-form-grid">
          <label className="settings-field"><span>İstifadəçi adı</span><input value={settings.user_name} onChange={e => update('user_name', e.target.value)} /></label>
          <label className="settings-field"><span>Müraciət forması</span><select value={settings.address_style} onChange={e => update('address_style', e.target.value)}><option value="Abdulla">Abdulla</option><option value="cənab Abdulla">Cənab Abdulla</option><option value="dostcasına">Dostcasına</option></select></label>
          <label className="settings-field"><span>Cavab uzunluğu</span><select value={settings.response_length} onChange={e => update('response_length', e.target.value)}><option value="short">Qısa</option><option value="normal">Normal</option><option value="detailed">Ətraflı</option></select></label>
          <label className="settings-field"><span>Səs tonu</span><select value={settings.voice_tone} onChange={e => update('voice_tone', e.target.value)}><option value="balanced">Balanslı</option><option value="professional">Professional</option><option value="friendly">Dostcanlı</option><option value="direct">Birbaşa</option></select></label>
        </div>
        <Range label="Yumor səviyyəsi" value={settings.humor_level} onChange={v => update('humor_level', v)} />
        <Range label="Proaktivlik səviyyəsi" value={settings.proactivity_level} onChange={v => update('proactivity_level', v)} />
        <label className="settings-field"><span>Advanced persona / system prompt</span><textarea value={settings.persona_prompt} placeholder="Əlavə persona qaydaları..." rows={4} onChange={e => update('persona_prompt', e.target.value)} /></label>
      </section>

      <section className="settings-section"><div className="settings-section-title"><FontAwesomeIcon icon={faMicrophone} /><span>VOICE & AUDIO</span><small>LIVE AUDIO</small></div>
        <div className="settings-form-grid"><label className="settings-field"><span>EVA səsi</span><select value={settings.voice} onChange={e => update('voice', e.target.value)}>{VOICES.map(v => <option key={v}>{v}</option>)}</select><small>Səs seçimi növbəti Live session-da tətbiq olunur.</small></label><label className="settings-field"><span>Fallback səs</span><select value={settings.fallback_voice} onChange={e => update('fallback_voice', e.target.value)}><option value="">Avtomatik</option>{VOICES.map(v => <option key={v}>{v}</option>)}</select></label></div>
        <Range label="Voice volume" value={settings.voice_volume} onChange={v => update('voice_volume', v)} /><Range label="Speech speed" value={settings.speech_speed} min={0.5} max={2} step={0.05} onChange={v => update('speech_speed', v)} />
        <div className="settings-toggle-grid"><label className="settings-control-row compact"><div><strong>Danışarkən interrupt</strong><small>EVA danışarkən istifadəçi sözünü kəsə bilər</small></div><Toggle value={settings.interrupt_enabled} onChange={() => update('interrupt_enabled', !settings.interrupt_enabled)} /></label><label className="settings-control-row compact"><div><strong>Auto-duck music</strong><small>EVA danışanda media səsini avtomatik azalt</small></div><Toggle value={settings.auto_duck_music} onChange={() => update('auto_duck_music', !settings.auto_duck_music)} /></label></div>
      </section>

      <section className="settings-section"><div className="settings-section-title"><FontAwesomeIcon icon={faVolumeHigh} /><span>SFX</span><small>AUDIO FEEDBACK</small></div>
        <div className="settings-control-row"><div><strong>Master SFX</strong><small>HUD və sistem feedback səsləri</small></div><Toggle value={settings.sfx_enabled} onChange={() => update('sfx_enabled', !settings.sfx_enabled)} /></div>
        <label className="settings-range"><div><span>Master volume</span><strong>{sfxLabel}</strong></div><input type="range" min="0" max="100" value={settings.sfx_volume} disabled={!settings.sfx_enabled} onChange={e => update('sfx_volume', Number(e.target.value))} /></label>
        <div className="settings-form-grid">{sfxItems.map(([label, enabledKey, volumeKey]) => <div className="settings-control-row compact" key={label}><div><strong>{label}</strong></div><Toggle value={Boolean(settings[enabledKey])} onChange={() => update(enabledKey, !Boolean(settings[enabledKey]))} /><input className="sfx-mini-range" type="range" min="0" max="100" value={Number(settings[volumeKey])} onChange={e => update(volumeKey, Number(e.target.value))} /></div>)}</div>
      </section>

      <section className="settings-section"><div className="settings-section-title"><FontAwesomeIcon icon={faAtom} /><span>EVA ORB</span><small>VISUAL ENGINE</small></div>
        <div className="settings-form-grid"><label className="settings-field"><span>Orb style</span><select value={settings.orb_style} onChange={e => update('orb_style', e.target.value)}><option value="default">EVA Core</option><option value="minimal">Minimal</option><option value="dense">Dense</option></select></label><label className="settings-field"><span>Listening color (RGB)</span><input value={settings.orb_listening_color} onChange={e => update('orb_listening_color', e.target.value)} /></label><label className="settings-field"><span>Speaking color (RGB)</span><input value={settings.orb_speaking_color} onChange={e => update('orb_speaking_color', e.target.value)} /></label><label className="settings-field"><span>Thinking color (RGB)</span><input value={settings.orb_thinking_color} onChange={e => update('orb_thinking_color', e.target.value)} /></label><label className="settings-field"><span>Muted color (RGB)</span><input value={settings.orb_muted_color} onChange={e => update('orb_muted_color', e.target.value)} /></label></div>
        <Range label="Particle density" value={settings.particle_density} onChange={v => update('particle_density', v)} /><Range label="Particle speed" value={settings.particle_speed} onChange={v => update('particle_speed', v)} /><Range label="Glow intensity" value={settings.glow_intensity} onChange={v => update('glow_intensity', v)} />
        <div className="settings-toggle-grid"><label className="settings-control-row compact"><div><strong>Particle animation</strong></div><Toggle value={settings.particle_animation_enabled} onChange={() => update('particle_animation_enabled', !settings.particle_animation_enabled)} /></label><label className="settings-control-row compact"><div><strong>Glow</strong></div><Toggle value={settings.glow_enabled} onChange={() => update('glow_enabled', !settings.glow_enabled)} /></label><label className="settings-control-row compact"><div><strong>Pulse</strong></div><Toggle value={settings.pulse_enabled} onChange={() => update('pulse_enabled', !settings.pulse_enabled)} /></label><label className="settings-control-row compact"><div><strong>Audio reactive</strong></div><Toggle value={settings.audio_reactive_enabled} onChange={() => update('audio_reactive_enabled', !settings.audio_reactive_enabled)} /></label></div>
      </section>

      <section className="settings-section"><div className="settings-section-title"><FontAwesomeIcon icon={faGoogle} /><span>GOOGLE HESABI</span><small>OAUTH 2.0</small></div><div className="settings-control-row google-account-row"><div className="google-account-info">{settings.google_account.connected && <div className="google-avatar">{settings.google_account.picture ? <img src={settings.google_account.picture} alt="Google profil şəkli" /> : <span>G</span>}</div>}<div><strong>{settings.google_account.connected ? settings.google_account.email || 'Google hesabı qoşulub' : 'Google hesabı qoşulmayıb'}</strong><small>{settings.google_account.connected ? 'Gmail · Calendar · Contacts · Tasks aktivdir' : 'EVA inteqrasiyalarını aktivləşdirmək üçün hesabını bir dəfə qoş.'}</small></div></div>{settings.google_account.connected ? <button className="settings-action secondary" disabled={googleBusy} onClick={() => googleAction('google.disconnect')}>{googleBusy ? 'GÖZLƏ...' : 'HESABDAN ÇIX'}</button> : <button className="settings-action" disabled={googleBusy} onClick={() => googleAction('google.connect')}>{googleBusy ? 'GOOGLE AÇILIR...' : 'GOOGLE HESABINI QOŞ'}</button>}</div></section>

      <section className="settings-section"><div className="settings-section-title"><FontAwesomeIcon icon={faKey} /><span>API AÇARLARI</span><small>SECURE</small></div><div className="settings-form-grid">
        <label className="settings-field"><span>Gemini API Key</span><div className="secret-input"><input type={showGemini ? 'text' : 'password'} value={settings.gemini_api_key} placeholder="Dəyişmək üçün yeni açar daxil et" onFocus={() => clearSecretForEdit('gemini_api_key')} onChange={e => update('gemini_api_key', e.target.value)} /><button type="button" onClick={() => setShowGemini(v => !v)}><FontAwesomeIcon icon={showGemini ? faEyeSlash : faEye} /></button></div><small>API açarı brauzerə tam formada qaytarılmır.</small></label>
        <label className="settings-field"><span>YouTube API Key</span><div className="secret-input"><input type={showYoutube ? 'text' : 'password'} value={settings.youtube_api_key} placeholder="Dəyişmək üçün yeni açar daxil et" onFocus={() => clearSecretForEdit('youtube_api_key')} onChange={e => update('youtube_api_key', e.target.value)} /><button type="button" onClick={() => setShowYoutube(v => !v)}><FontAwesomeIcon icon={showYoutube ? faEyeSlash : faEye} /></button></div></label>
        <label className="settings-field"><span>YouTube Channel Handle</span><input value={settings.youtube_channel_handle} placeholder="@kanal" onChange={e => update('youtube_channel_handle', e.target.value)} /></label>
      </div></section>

      <section className="settings-section"><div className="settings-section-title"><FontAwesomeIcon icon={faSliders} /><span>EVA DAVRANIŞI</span><small>RUNTIME</small></div><div className="settings-form-grid"><label className="settings-field"><span>Dil</span><select value={settings.language} onChange={e => update('language', e.target.value)}><option value="az-AZ">Azərbaycan dili</option><option value="en-US">English</option><option value="tr-TR">Türkçe</option></select></label></div><div className="settings-toggle-grid"><label className="settings-control-row compact"><div><strong>Proaktiv bildirişlər</strong><small>EVA özü bildiriş yarada bilər</small></div><Toggle value={settings.proactive_enabled} onChange={() => update('proactive_enabled', !settings.proactive_enabled)} /></label><label className="settings-control-row compact"><div><strong>Wake listener</strong><small>Wake listener aktiv olsun</small></div><Toggle value={settings.wake_listener_enabled} onChange={() => update('wake_listener_enabled', !settings.wake_listener_enabled)} /></label><label className="settings-control-row compact"><div><strong>Avtomatik başlatma</strong><small>Sistem açılışında EVA-nı işə sal</small></div><Toggle value={settings.auto_start} onChange={() => update('auto_start', !settings.auto_start)} /></label></div></section>
    </main>
    <footer className="settings-footer"><span className={status.includes('YADDA') || status.includes('QOŞULDU') ? 'success' : ''}>{status || 'Dəyişikliklər hazırdır'}</span><button className="save-settings" disabled={saving} onClick={save}><FontAwesomeIcon icon={saving ? faGear : faCheck} /> {saving ? 'YADDA SAXLANILIR' : 'YADDA SAXLA'}</button></footer>
  </div>;
}

export function SettingsHost() {
  const [open, setOpen] = useState(false);
  useEffect(() => { const handleClick = (event: MouseEvent) => { const target = event.target as HTMLElement | null; if (target?.closest('.settings')) { event.preventDefault(); setOpen(true); } }; document.addEventListener('click', handleClick); return () => document.removeEventListener('click', handleClick); }, []);
  if (!open) return null;
  return <SettingsPage onClose={() => setOpen(false)} />;
}
