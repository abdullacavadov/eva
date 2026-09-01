import { useState } from "react";

const AY_ADLARI = [
  "Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun",
  "İyul", "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr",
];

const HEFTE_GUNLERI = ["B.e", "Ç.a", "Ç", "C.a", "C", "Ş", "B"];

export default function AzCalendar() {
  const bugun = new Date();
  const [ay, setAy] = useState(bugun.getMonth());
  const [il, setIl] = useState(bugun.getFullYear());
  const [ilAcig, setIlAcig] = useState(false);

  const ayDeyis = (deger:number) => {
    let ya = ay + deger, yi = il;
    if (ya < 0) { ya = 11; yi -= 1; }
    if (ya > 11) { ya = 0; yi += 1; }
    setAy(ya); setIl(yi);
  };

  const ilSiyahisi = Array.from({ length: 12 }, (_, i) => il - 6 + i);
  const ilkGun = new Date(il, ay, 1).getDay();
  const basSutunu = ilkGun === 0 ? 6 : ilkGun - 1;
  const gunSayi = new Date(il, ay + 1, 0).getDate();
  const hucreler = [...Array(basSutunu).fill(null), ...Array.from({ length: gunSayi }, (_, i) => i + 1)];

  return (
    <div className="azc">
      <style>{`
        .azc {
          --ink: #211f1c;
          --paper: #fbfaf7;
          --line: #e1ddd3;
          --muted: #9a9184;
          --accent: #2f5d54;
          --accent-soft: #e3ece9;
          width: 320px;
          background: var(--paper);
          border: 1px solid var(--line);
          font-family: 'Georgia', 'Iowan Old Style', serif;
          color: var(--ink);
        }
        .azc-top {
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          padding: 18px 16px 14px;
          border-bottom: 1px solid var(--line);
        }
        .azc-nav { display: flex; gap: 2px; }
        .azc-navbtn {
          width: 26px; height: 26px; border: none; background: transparent;
          color: var(--ink); font-family: inherit; font-size: 16px; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          border-radius: 3px; transition: background 0.15s ease;
        }
        .azc-navbtn:hover { background: var(--accent-soft); color: var(--accent); }
        .azc-month { text-align: center; font-size: 18px; letter-spacing: 0.02em; font-style: italic; }
        .azc-year-wrap { position: relative; text-align: right; }
        .azc-year {
          border: none; background: transparent; font-family: inherit; font-size: 14px;
          color: var(--muted); cursor: pointer; padding: 2px 4px; border-bottom: 1px solid transparent;
        }
        .azc-year:hover { color: var(--ink); border-bottom: 1px solid var(--ink); }
        .azc-year-list {
          position: absolute; right: 0; top: 26px; background: var(--paper);
          border: 1px solid var(--line); max-height: 180px; overflow-y: auto; z-index: 5;
          box-shadow: 0 4px 10px rgba(0,0,0,0.06);
        }
        .azc-year-item {
          display: block; width: 100%; text-align: right; padding: 6px 14px;
          border: none; background: transparent; font-family: inherit; font-size: 13px;
          color: var(--ink); cursor: pointer;
        }
        .azc-year-item:hover { background: var(--accent-soft); }
        .azc-year-item.aktiv { color: var(--accent); font-weight: 600; }
        .azc-heftegun {
          display: grid; grid-template-columns: repeat(7, 1fr); padding: 10px 10px 2px;
          font-family: -apple-system, sans-serif; font-size: 10.5px; letter-spacing: 0.06em;
          color: var(--muted); text-align: center;
        }
        .azc-gunler { display: grid; grid-template-columns: repeat(7, 1fr); padding: 4px 10px 16px; font-family: -apple-system, sans-serif; }
        .azc-hucre { display: flex; align-items: center; justify-content: center; height: 36px; }
        .azc-gun {
          width: 28px; height: 28px; border: none; background: transparent; font-family: inherit;
          font-size: 13px; color: var(--ink); cursor: pointer; border-radius: 50%; transition: background 0.15s ease;
        }
        .azc-gun:hover { background: var(--accent-soft); }
        .azc-gun.bugun { background: var(--accent); color: #fff; }
      `}</style>

      <div className="azc-top">
        <div className="azc-nav">
          <button className="azc-navbtn" onClick={() => ayDeyis(-1)} aria-label="Əvvəlki ay">‹</button>
          <button className="azc-navbtn" onClick={() => ayDeyis(1)} aria-label="Növbəti ay">›</button>
        </div>
        <div className="azc-month">{AY_ADLARI[ay]}</div>
        <div className="azc-year-wrap">
          <button className="azc-year" onClick={() => setIlAcig(!ilAcig)}>{il}</button>
          {ilAcig && (
            <div className="azc-year-list">
              {ilSiyahisi.map((y) => (
                <button
                  key={y}
                  className={`azc-year-item${y === il ? " aktiv" : ""}`}
                  onClick={() => { setIl(y); setIlAcig(false); }}
                >
                  {y}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="azc-heftegun">
        {HEFTE_GUNLERI.map((g) => <div key={g}>{g}</div>)}
      </div>

      <div className="azc-gunler">
        {hucreler.map((gun, idx) => {
          const buGunMu = gun === bugun.getDate() && ay === bugun.getMonth() && il === bugun.getFullYear();
          return (
            <div key={idx} className="azc-hucre">
              {gun && (
                <button className={`azc-gun${buGunMu ? " bugun" : ""}`}>{gun}</button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}