import { useEffect, useRef, useState, type CSSProperties } from 'react';
import * as d3 from 'd3';
import type { FeatureCollection, Geometry } from 'geojson';
import type { EvaState } from '../types/eva';

const EARTH_DATA_URL =
  'https://raw.githubusercontent.com/martynafford/natural-earth-geojson/refs/heads/master/110m/physical/ne_110m_land.json';

interface OrbProps {
  state: EvaState;
}

interface LandProperties {
  [key: string]: unknown;
}

type LandData = FeatureCollection<Geometry, LandProperties>;

interface EarthDot {
  longitude: number;
  latitude: number;
}

const EARTH_ROTATION_SPEED = 0.5;
const EARTH_DOT_STEP = 1.7;
const EARTH_DOT_RADIUS = 0.85;
const WAVE_COLOR = '0,255,192';

const STATE_COLORS: Record<EvaState, [number, number, number]> = {
  IDLE: [0, 255, 136],
  LISTENING: [0, 255, 136],
  SPEAKING: [68, 136, 255],
  THINKING: [255, 204, 0],
  EXECUTING: [68, 136, 255],
  WAITING_CONFIRMATION: [255, 204, 0],
  SUCCESS: [0, 255, 136],
  MUTED: [200, 30, 80],
  PAUSED: [30, 60, 55],
  ERROR: [255, 51, 68],
  INITIALISING: [255, 51, 68],
};

export function EvaOrb({ state }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const landRef = useRef<LandData | null>(null);
  const dotsRef = useRef<EarthDot[]>([]);
  const rotationRef = useRef<[number, number, number]>([0, -8, 0]);
  const zoomRef = useRef(1);
  const draggingRef = useRef(false);
  const lastPointerRef = useRef<[number, number] | null>(null);
  const animationRef = useRef<number | null>(null);
  const audioLevelRef = useRef(0);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');

  useEffect(() => {
    let cancelled = false;

    const loadEarth = async () => {
      try {
        const response = await fetch(EARTH_DATA_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = (await response.json()) as LandData;
        if (cancelled) return;

        landRef.current = data;
        dotsRef.current = createLandDots(data);
        setStatus('ready');
      } catch {
        if (!cancelled) setStatus('error');
      }
    };

    loadEarth();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleAudioLevel = (event: Event) => {
      const level = (event as CustomEvent<number>).detail;
      audioLevelRef.current = Math.max(0, Math.min(1, Number(level) || 0));
    };

    window.addEventListener('eva:audio-level', handleAudioLevel);
    return () => window.removeEventListener('eva:audio-level', handleAudioLevel);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    let width = 0;
    let height = 0;
    let radius = 0;

    const resize = () => {
      const rect = wrapper.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      radius = Math.min(width, height) * 0.43 * zoomRef.current;

      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const observer = new ResizeObserver(resize);
    observer.observe(wrapper);
    resize();

    const drawWave = (centerX: number, centerY: number) => {
      if (state !== 'SPEAKING') return;

      const level = audioLevelRef.current;
      const waveWidth = Math.min(width * 0.78, radius * 2.1);
      const startX = centerX - waveWidth / 2;
      const segmentCount = 80;
      const lineCount = 7;
      const baseAmplitude = 2 + Math.pow(level, 0.65) * 34;
      const waveY = Math.min(height - 24, centerY + radius + 24);

      context.save();
      context.lineWidth = 1.2;
      context.lineCap = 'round';
      context.lineJoin = 'round';

      for (let i = 0; i < lineCount; i++) {
        context.beginPath();
        const progress = i / (lineCount - 1);
        const intensity = Math.sin(progress * Math.PI);
        context.strokeStyle = `rgba(${WAVE_COLOR},${0.12 + intensity * 0.28})`;

        for (let j = 0; j <= segmentCount; j++) {
          const x = startX + (j / segmentCount) * waveWidth;
          const phase = i * 0.22;
          const noise = Math.sin(j * 0.1 + performance.now() * 0.004 + phase) * baseAmplitude * 0.45;
          const spike =
            Math.cos(j * 0.2 + performance.now() * 0.005 + phase) *
            Math.sin(j * 0.05 + performance.now() * 0.003) *
            baseAmplitude;
          const y = waveY + noise + spike * intensity;

          if (j === 0) context.moveTo(x, y);
          else context.lineTo(x, y);
        }
        context.stroke();
      }

      context.restore();
    };

    const draw = () => {
      const [red, green, blue] = STATE_COLORS[state];
      const stateRgb = `${red},${green},${blue}`;

      context.clearRect(0, 0, width, height);
      if (radius <= 0) {
        animationRef.current = requestAnimationFrame(draw);
        return;
      }

      const centerX = width / 2;
      const centerY = height / 2 - 12;
      const projection = d3
        .geoOrthographic()
        .translate([centerX, centerY])
        .scale(radius)
        .rotate(rotationRef.current)
        .clipAngle(90);
      const path = d3.geoPath(projection, context);

      context.save();
      context.beginPath();
      path({ type: 'Sphere' });
      context.fillStyle = '#000';
      context.fill();
      context.strokeStyle = `rgba(${stateRgb},0.95)`;
      context.lineWidth = 1.4;
      context.shadowColor = `rgba(${stateRgb},0.55)`;
      context.shadowBlur = state === 'PAUSED' ? 8 : 20;
      context.stroke();
      context.shadowBlur = 0;

      const graticule = d3.geoGraticule().step([15, 15]);
      context.beginPath();
      path(graticule());
      context.strokeStyle = `rgba(${stateRgb},0.25)`;
      context.lineWidth = 0.55;
      context.stroke();

      const land = landRef.current;
      if (land) {
        context.beginPath();
        land.features.forEach((feature) => path(feature));
        context.strokeStyle = `rgba(${stateRgb},0.7)`;
        context.lineWidth = 0.7;
        context.stroke();

        context.fillStyle = `rgba(${stateRgb},0.88)`;
        dotsRef.current.forEach((dot) => {
          const point = projection([dot.longitude, dot.latitude]);
          if (!point) return;
          context.beginPath();
          context.arc(point[0], point[1], EARTH_DOT_RADIUS, 0, Math.PI * 2);
          context.fill();
        });
      }

      context.restore();
      drawWave(centerX, centerY);

      if (!draggingRef.current && landRef.current && state !== 'PAUSED') {
        rotationRef.current[0] += EARTH_ROTATION_SPEED;
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    animationRef.current = requestAnimationFrame(draw);

    return () => {
      observer.disconnect();
      if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    };
  }, [state]);

  const handlePointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    draggingRef.current = true;
    lastPointerRef.current = [event.clientX, event.clientY];
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!draggingRef.current || !lastPointerRef.current) return;

    const [lastX, lastY] = lastPointerRef.current;
    const dx = event.clientX - lastX;
    const dy = event.clientY - lastY;
    const rotation = rotationRef.current;

    rotation[0] += dx * 0.45;
    rotation[1] -= dy * 0.35;
    rotation[1] = Math.max(-80, Math.min(80, rotation[1]));
    lastPointerRef.current = [event.clientX, event.clientY];
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
    draggingRef.current = false;
    lastPointerRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  };

  const handleWheel = (event: React.WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    zoomRef.current = Math.max(
      0.72,
      Math.min(1.35, zoomRef.current * (event.deltaY > 0 ? 0.92 : 1.08))
    );
  };

  const canvasStyle: CSSProperties = {
    width: '100%',
    height: '100%',
    display: 'block',
    cursor: status === 'ready' ? 'grab' : 'default',
    touchAction: 'none',
  };

  return (
    <div
      ref={wrapperRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 320,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <canvas
        ref={canvasRef}
        style={canvasStyle}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onWheel={handleWheel}
      />
      {status === 'loading' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'rgba(255,255,255,0.7)',
            fontSize: 12,
            letterSpacing: '0.12em',
          }}
        >
          YÜKLƏNİR...
        </div>
      )}
      {status === 'error' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'rgba(255,255,255,0.7)',
            fontSize: 12,
            letterSpacing: '0.08em',
          }}
        >
          YÜKLƏMƏ XƏTASI
        </div>
      )}
    </div>
  );
}

function createLandDots(data: LandData): EarthDot[] {
  const dots: EarthDot[] = [];
  const step = EARTH_DOT_STEP;

  for (let latitude = -90 + step / 2; latitude < 90; latitude += step) {
    const longitudeOffset =
      (Math.floor((latitude + 90) / step) % 2) * (step / 2);
    for (
      let longitude = -180 + longitudeOffset;
      longitude < 180;
      longitude += step
    ) {
      if (d3.geoContains(data, [longitude, latitude])) {
        dots.push({ longitude, latitude });
      }
    }
  }

  return dots;
}
