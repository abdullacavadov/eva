import { useEffect, useRef, useState, type CSSProperties } from 'react';
import * as d3 from 'd3';
import type { FeatureCollection, Geometry } from 'geojson';
import type { EvaState } from '../types/eva';

interface OrbProps {
  state: EvaState;
}

interface LandProperties {
  [key: string]: unknown;
}

interface WaveDustParticle {
  xNorm0: number;
  yNorm: number; // -1..1, envelope daxilində sabit nisbi mövqe
  r: number;
  baseAlpha: number;
  driftSpeed: number;
  twinkleSpeed: number;
  twinklePhase: number;
}

const WAVE_DUST_COUNT = 36;
const WAVE_DUST_RGB = '69,217,255'; // WAVE_COLOR (#45d9ff) → rgb

function createWaveDust(count: number): WaveDustParticle[] {
  const particles: WaveDustParticle[] = [];
  for (let i = 0; i < count; i++) {
    particles.push({
      xNorm0: Math.random(),
      yNorm: (Math.random() - 0.5) * 2,
      r: 0.5 + Math.random() * 1,
      baseAlpha: 0.1 + Math.random() * 0.3,
      driftSpeed: 0.00002 + Math.random() * 0.00006,
      twinkleSpeed: 0.001 + Math.random() * 0.003,
      twinklePhase: Math.random() * Math.PI * 2,
    });
  }
  return particles;
}

type LandData = FeatureCollection<Geometry, LandProperties>;

interface SatelliteOrbit {
  tilt: number;
  rotation: number;
  radiusX: number;
  radiusY: number;
  speed: number;
  phase: number;
}

interface StarParticle {
  x: number; // normalized -1..1 relative to wrapper
  y: number;
  r: number;
  baseAlpha: number;
  twinkleSpeed: number;
  twinklePhase: number;
  parallax: number; // depth factor for drift
}

const EARTH_ROTATION_SPEED = 0.5;
const WAVE_COLOR = '#45d9ff';
const SATELLITE_COLOR = '0,255,192';
const STAR_COUNT = 90;

const SATELLITE_ORBITS: SatelliteOrbit[] = [
  {
    tilt: 1.15,
    rotation: 0.2,
    radiusX: 1.05,
    radiusY: 1.0,
    speed: 0.0022,
    phase: 0,
  },
  {
    tilt: -1.3,
    rotation: 1.1,
    radiusX: 1.08,
    radiusY: 1.0,
    speed: -0.0017,
    phase: 2.1,
  },
  {
    tilt: 0.9,
    rotation: 2.0,
    radiusX: 1.04,
    radiusY: 1.0,
    speed: 0.0015,
    phase: 4.2,
  },
  {
    tilt: -0.75,
    rotation: 2.9,
    radiusX: 1.1,
    radiusY: 1.0,
    speed: -0.0012,
    phase: 5.4,
  },
];

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

function createStarField(count: number): StarParticle[] {
  const stars: StarParticle[] = [];
  for (let i = 0; i < count; i++) {
    stars.push({
      x: (Math.random() - 0.5) * 2,
      y: (Math.random() - 0.5) * 2,
      r: 0.4 + Math.random() * 1.3,
      baseAlpha: 0.15 + Math.random() * 0.5,
      twinkleSpeed: 0.0006 + Math.random() * 0.0018,
      twinklePhase: Math.random() * Math.PI * 2,
      parallax: 0.15 + Math.random() * 0.5,
    });
  }
  return stars;
}

export function EvaOrb({ state }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const landRef = useRef<LandData | null>(null);
  const starsRef = useRef<StarParticle[]>(createStarField(STAR_COUNT));
  const waveDustRef = useRef<WaveDustParticle[]>(
    createWaveDust(WAVE_DUST_COUNT)
  );
  const rotationRef = useRef<[number, number, number]>([0, -8, 0]);
  const zoomRef = useRef(1);
  const draggingRef = useRef(false);
  const lastPointerRef = useRef<[number, number] | null>(null);
  const animationRef = useRef<number | null>(null);
  const audioLevelRef = useRef(0);
  const satelliteTimeRef = useRef(0);
  const pulseStartRef = useRef<number | null>(null);
  const prevStateRef = useRef<EvaState>(state);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>(
    'loading'
  );

  useEffect(() => {
    let cancelled = false;

    const loadEarth = async () => {
      try {
        const response = await fetch('./earth_globe.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = (await response.json()) as LandData;
        if (cancelled) return;

        landRef.current = data;
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
    return () =>
      window.removeEventListener('eva:audio-level', handleAudioLevel);
  }, []);

  // Trigger a pulse whenever state changes
  useEffect(() => {
    if (prevStateRef.current !== state) {
      pulseStartRef.current = performance.now();
      prevStateRef.current = state;
    }
  }, [state]);

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

    // ---- Atmosphere particle field (background) ----
    const drawStars = (
      centerX: number,
      centerY: number,
      now: number,
      stateRgb: string
    ) => {
      const drift = now * 0.00002;
      context.save();
      starsRef.current.forEach((star) => {
        const driftX =
          star.x +
          Math.sin(drift * star.parallax * 6 + star.twinklePhase) * 0.03;
        const driftY =
          star.y +
          Math.cos(drift * star.parallax * 6 + star.twinklePhase) * 0.03;
        const px = centerX + driftX * width * 0.55;
        const py = centerY + driftY * height * 0.55;

        // skip stars that fall inside the globe so they don't overpower it
        const distFromCenter = Math.hypot(px - centerX, py - centerY);
        if (distFromCenter < radius * 1.05) return;

        const twinkle =
          0.5 + 0.5 * Math.sin(now * star.twinkleSpeed + star.twinklePhase);
        const alpha = star.baseAlpha * (0.4 + twinkle * 0.6);

        context.beginPath();
        context.arc(px, py, star.r, 0, Math.PI * 2);
        context.fillStyle = `rgba(${stateRgb},${alpha * 0.6})`;
        context.fill();
      });
      context.restore();
    };

    // ---- Atmosphere halo (rim glow around globe) ----
    const drawHalo = (
      centerX: number,
      centerY: number,
      now: number,
      stateRgb: string
    ) => {
      const pulseStart = pulseStartRef.current;
      let pulseBoost = 0;
      if (pulseStart !== null) {
        const elapsed = now - pulseStart;
        const duration = 500;
        if (elapsed < duration) {
          const t = elapsed / duration;
          pulseBoost = Math.sin(t * Math.PI) * 0.25;
        } else {
          pulseStartRef.current = null;
        }
      }

      const outer = radius * (1.32 + pulseBoost);
      const grad = context.createRadialGradient(
        centerX,
        centerY,
        radius * 0.97,
        centerX,
        centerY,
        outer
      );
      grad.addColorStop(0, `rgba(${stateRgb},${0.32 + pulseBoost * 0.4})`);
      grad.addColorStop(1, `rgba(${stateRgb},0)`);

      context.save();
      context.beginPath();
      context.arc(centerX, centerY, outer, 0, Math.PI * 2);
      context.fillStyle = grad;
      context.fill();
      context.restore();
    };

    // ---- Radar sweep across the globe surface ----
    const drawScanSweep = (
      centerX: number,
      centerY: number,
      now: number,
      spherePath: () => void
    ) => {
      const scanY = centerY + Math.sin(now * 0.0006) * radius * 0.92;

      context.save();
      context.beginPath();
      spherePath();
      context.clip();

      const grad = context.createLinearGradient(
        centerX - radius,
        scanY,
        centerX + radius,
        scanY
      );
      grad.addColorStop(0, 'rgba(69,217,255,0)');
      grad.addColorStop(0.5, 'rgba(69,217,255,0.16)');
      grad.addColorStop(1, 'rgba(69,217,255,0)');
      context.fillStyle = grad;
      context.fillRect(centerX - radius, scanY - 2, radius * 2, 4);
      context.restore();
    };

    const drawSatellites = (
      centerX: number,
      centerY: number,
      now: number,
      stateRgb: string
    ) => {
      satelliteTimeRef.current = now;
      const activeColor = SATELLITE_COLOR;
      const paused = state === 'PAUSED';
      const time = paused ? satelliteTimeRef.current : now;
      const squash = 0.9;

      context.save();
      context.lineCap = 'round';

      SATELLITE_ORBITS.forEach((orbit) => {
        const R = radius * orbit.radiusX;
        const cosR = Math.cos(orbit.rotation);
        const sinR = Math.sin(orbit.rotation);
        const cosT = Math.cos(orbit.tilt);
        const sinT = Math.sin(orbit.tilt);


        const project = (theta: number) => {
          const x0 = Math.cos(theta) * R;
          const y0 = Math.sin(theta) * R;
          const y1 = y0 * cosT;
          const z1 = y0 * sinT;
          const x2 = x0 * cosR - y1 * sinR;
          const y2 = x0 * sinR + y1 * cosR;
          const sx = centerX + x2;
          const sy = centerY + y2 * squash;
          const depth = z1 / R;
          const dist = Math.hypot(x2, y2 * squash);
          const hidden = depth < 0 && dist < radius * 0.995; // artıq işə düşəcək
          return { sx, sy, depth, hidden };
        };

        // Orbit ring + HUD ticks
        for (let i = 0; i < 200; i++) {
          const t0 = (i / 200) * Math.PI * 2;
          const t1 = ((i + 1) / 200) * Math.PI * 2;
          const p0 = project(t0);
          const p1 = project(t1);
          if (p0.hidden || p1.hidden) continue;

          const depthT = Math.max(0, (p0.depth + 1) / 2);
          context.beginPath();
          context.moveTo(p0.sx, p0.sy);
          context.lineTo(p1.sx, p1.sy);
          context.strokeStyle = `rgba(${stateRgb},${0.1 + depthT * 0.22})`;
          context.lineWidth = 0.5 + depthT * 0.7;
          context.stroke();

          if (i % 14 === 0) {
            const nx = (p0.sx - centerX) / R;
            const ny = (p0.sy - centerY) / R;
            const tickLen = 3 + depthT * 3;
            context.beginPath();
            context.moveTo(p0.sx, p0.sy);
            context.lineTo(p0.sx + nx * tickLen, p0.sy + ny * tickLen);
            context.strokeStyle = `rgba(${activeColor},${0.35 * depthT})`;
            context.lineWidth = 1;
            context.stroke();
          }
        }

        // Peyk
        const satelliteAngle = orbit.phase + time * orbit.speed;
        const sat = project(satelliteAngle);
        if (sat.hidden) return;

        const depthT = Math.max(0, (sat.depth + 1) / 2);
        const scale = 0.7 + depthT * 0.5;

        // Gradient iz (parlaq baş -> şəffaf quyruq)
        let started = false;
        let prevPoint: { sx: number; sy: number } | null = null;
        for (let trail = 10; trail >= 0; trail--) {
          const tp = project(satelliteAngle - orbit.speed * 90 * (trail / 10));
          if (tp.hidden) {
            started = false;
            prevPoint = null;
            continue;
          }
          if (!started) {
            started = true;
            prevPoint = tp;
            continue;
          }
          const grad = context.createLinearGradient(
            prevPoint!.sx,
            prevPoint!.sy,
            tp.sx,
            tp.sy
          );
          const alphaNear = 0.5 * scale * (1 - trail / 11);
          const alphaFar = 0.5 * scale * (1 - (trail + 1) / 11);
          grad.addColorStop(
            0,
            `rgba(${activeColor},${Math.max(0, alphaNear)})`
          );
          grad.addColorStop(1, `rgba(${activeColor},${Math.max(0, alphaFar)})`);

          context.beginPath();
          context.moveTo(prevPoint!.sx, prevPoint!.sy);
          context.lineTo(tp.sx, tp.sy);
          context.strokeStyle = grad;
          context.lineWidth = scale;
          context.stroke();
          prevPoint = tp;
        }

        // Peyk cismi
        context.beginPath();
        context.arc(sat.sx, sat.sy, 2 * scale, 0, Math.PI * 2);
        context.fillStyle = `rgba(${activeColor},${0.9 * scale})`;
        context.shadowColor = `rgba(${activeColor},0.9)`;
        context.shadowBlur = paused ? 3 : 6 + depthT * 6;
        context.fill();
        context.shadowBlur = 0;

        context.beginPath();
        context.arc(sat.sx, sat.sy, 4 * scale, 0, Math.PI * 2);
        context.strokeStyle = `rgba(${activeColor},${0.2 * scale})`;
        context.lineWidth = 0.6;
        context.stroke();
      });

      context.restore();
    };

    const drawWave = (
      centerX: number,
      centerY: number,
      now: number,
      stateRgb: string
    ) => {
      if (state !== 'SPEAKING') return;

      const level = audioLevelRef.current;
      const waveWidth = width;
      const startX = centerX - waveWidth / 2;
      const segmentCount = 80;
      const lineCount = 7;
      const baseAmplitude = 2 + Math.pow(level, 0.65) * 34;
      const waveY = Math.min(height - 24, centerY + radius + 24);

      // Bütün xətlərin y dəyərlərini əvvəlcədən hesabla
      const allYs: number[][] = [];
      for (let i = 0; i < lineCount; i++) {
        const progress = i / (lineCount - 1);
        const intensity = Math.sin(progress * Math.PI);
        const phase = i * 0.22;
        const ys: number[] = [];
        for (let j = 0; j <= segmentCount; j++) {
          const t = j / segmentCount; // 0..1
          const edgeFade = Math.sin(t * Math.PI); // 0 kənarlarda, 1 mərkəzdə

          const noise =
            Math.sin(j * 0.1 + now * 0.004 + phase) * baseAmplitude * 0.45;
          const spike =
            Math.cos(j * 0.2 + now * 0.005 + phase) *
            Math.sin(j * 0.05 + now * 0.003) *
            baseAmplitude;
          ys.push(waveY + (noise + spike * intensity) * edgeFade);
        }
        allYs.push(ys);
      }

      // Hər x nöqtəsində min/max envelope
      const upperEnv: number[] = [];
      const lowerEnv: number[] = [];
      for (let j = 0; j <= segmentCount; j++) {
        let mn = Infinity;
        let mx = -Infinity;
        for (let i = 0; i < lineCount; i++) {
          const y = allYs[i][j];
          if (y < mn) mn = y;
          if (y > mx) mx = y;
        }
        upperEnv.push(mn);
        lowerEnv.push(mx);
      }

      const envelopePath = () => {
        context.moveTo(startX, upperEnv[0]);
        for (let j = 1; j <= segmentCount; j++) {
          const x = startX + (j / segmentCount) * waveWidth;
          context.lineTo(x, upperEnv[j]);
        }
        for (let j = segmentCount; j >= 0; j--) {
          const x = startX + (j / segmentCount) * waveWidth;
          context.lineTo(x, lowerEnv[j]);
        }
        context.closePath();
      };

      // ---- Sahəni rəngləmə (gradient fill) ----
      context.save();
      context.beginPath();
      envelopePath();
      const fillGrad = context.createLinearGradient(
        0,
        waveY - baseAmplitude * 1.45,
        0,
        waveY + baseAmplitude * 1.45
      );
      fillGrad.addColorStop(0, 'rgba(69,217,255,0.1)');
      fillGrad.addColorStop(0.5, 'rgba(69,217,255,0.25)');
      fillGrad.addColorStop(1, 'rgba(69,217,255,0.1)');
      context.fillStyle = fillGrad;
      context.fill();
      context.restore();

      // ---- İncə toz toxuması (yalnız sahə daxilində, clip ilə) ----
      context.save();
      context.beginPath();
      envelopePath();
      context.clip();

      waveDustRef.current.forEach((p) => {
        const xNorm = (p.xNorm0 + now * p.driftSpeed) % 1;
        const x = startX + xNorm * waveWidth;
        const j = Math.round(xNorm * segmentCount);
        const yTop = upperEnv[j] ?? waveY;
        const yBot = lowerEnv[j] ?? waveY;
        const y = yTop + ((p.yNorm + 1) / 2) * (yBot - yTop);

        const twinkle =
          0.5 + 0.5 * Math.sin(now * p.twinkleSpeed + p.twinklePhase);
        const alpha = p.baseAlpha * (0.3 + twinkle * 0.7);

        context.beginPath();
        context.arc(x, y, p.r, 0, Math.PI * 2);
        context.fillStyle = `rgba(${WAVE_DUST_RGB},${alpha})`;
        context.fill();
      });
      context.restore();

      // ---- Dalğa xətləri (rənglənmiş sahənin üstündə) ----
      context.save();
      context.lineWidth = 1.2;
      context.lineCap = 'round';
      context.lineJoin = 'round';
      context.strokeStyle = `rgba(${stateRgb},1)`;

      for (let i = 0; i < lineCount; i++) {
        context.beginPath();
        for (let j = 0; j <= segmentCount; j++) {
          const x = startX + (j / segmentCount) * waveWidth;
          const y = allYs[i][j];
          if (j === 0) context.moveTo(x, y);
          else context.lineTo(x, y);
        }
        context.stroke();
      }

      context.restore();
    };

    const draw = (timestamp: number) => {
      const [red, green, blue] = STATE_COLORS[state];
      const stateRgb = `${red},${green},${blue}`;

      context.clearRect(0, 0, width, height);
      if (radius <= 0) {
        animationRef.current = requestAnimationFrame(draw);
        return;
      }

      const centerX = width / 2;
      const centerY = height / 2 - 12;

      drawStars(centerX, centerY, timestamp, stateRgb);
      drawHalo(centerX, centerY, timestamp, stateRgb);

      const projection = d3
        .geoOrthographic()
        .translate([centerX, centerY])
        .scale(radius)
        .rotate(rotationRef.current)
        .clipAngle(90);
      const path = d3.geoPath(projection, context);
      const spherePathFn = () => path({ type: 'Sphere' });

      context.save();
      context.beginPath();
      spherePathFn();
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

        context.fillStyle = `rgba(${stateRgb},0.3)`;
        context.fill();

        context.strokeStyle = `rgba(${stateRgb},0.7)`;
        context.lineWidth = 0.7;
        context.stroke();
      }
      context.restore();

      drawScanSweep(centerX, centerY, timestamp, spherePathFn);
      drawSatellites(centerX, centerY, timestamp, stateRgb);
      drawWave(centerX, centerY, timestamp, stateRgb);

      if (!draggingRef.current && landRef.current && state !== 'PAUSED') {
        rotationRef.current[0] += EARTH_ROTATION_SPEED;
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    animationRef.current = requestAnimationFrame(draw);

    return () => {
      observer.disconnect();
      if (animationRef.current !== null)
        cancelAnimationFrame(animationRef.current);
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
