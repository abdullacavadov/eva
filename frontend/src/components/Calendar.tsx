import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChevronLeft, faChevronRight } from '@fortawesome/free-solid-svg-icons';

const AY_ADLARI = [
  'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'İyun',
  'İyul', 'Avqust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr',
];

const HEFTE_GUNLERI = ['B.e', 'Ç.a', 'Ç', 'C.a', 'C', 'Ş', 'B'];

export default function AzCalendar() {
  const bugun = new Date();
  const [ay, setAy] = useState(bugun.getMonth());
  const [il, setIl] = useState(bugun.getFullYear());
  const [ilAcig, setIlAcig] = useState(false);

  const ayDeyis = (deger: number) => {
    let ya = ay + deger;
    let yi = il;
    if (ya < 0) { ya = 11; yi -= 1; }
    if (ya > 11) { ya = 0; yi += 1; }
    setAy(ya);
    setIl(yi);
    setIlAcig(false);
  };

  const ilSiyahisi = Array.from({ length: 12 }, (_, i) => il - 6 + i);
  const ilkGun = new Date(il, ay, 1).getDay();
  const basSutunu = ilkGun === 0 ? 6 : ilkGun - 1;
  const gunSayi = new Date(il, ay + 1, 0).getDate();
  const hucreler = [
    ...Array(basSutunu).fill(null),
    ...Array.from({ length: gunSayi }, (_, i) => i + 1),
  ];

  return (
    <section className="azc panel" aria-label="Təqvim">
      <style>{`
        .azc {
          width: 100%;
          flex: 0 0 auto;
          color: var(--text);
          background: linear-gradient(145deg, rgba(7, 22, 31, .92), rgba(3, 12, 19, .84));
        }
        .azc-top {
          display: grid;
          grid-template-columns: 54px 1fr 54px;
          align-items: center;
          min-height: 56px;
          padding: 8px 12px;
          border-bottom: 1px solid var(--line);
        }
        .azc-nav {
          display: flex;
          align-items: center;
          gap: 2px;
        }
        .azc-navbtn {
          width: 26px;
          height: 26px;
          display: grid;
          place-items: center;
          padding: 0;
          border: 1px solid transparent;
          border-radius: 6px;
          background: transparent;
          color: var(--muted);
          cursor: pointer;
          font-size: 10px;
          transition: .18s ease;
        }
        .azc-navbtn:hover {
          color: var(--cyan-bright);
          border-color: var(--line);
          background: rgba(69, 217, 255, .055);
          box-shadow: 0 0 12px rgba(69, 217, 255, .08);
        }
        .azc-month {
          text-align: center;
          color: #9edff1;
          font-size: 10px;
          font-weight: 500;
          letter-spacing: .16em;
          text-transform: uppercase;
        }
        .azc-year-wrap {
          position: relative;
          text-align: right;
        }
        .azc-year {
          border: 0;
          border-bottom: 1px solid transparent;
          background: transparent;
          color: var(--muted);
          cursor: pointer;
          padding: 3px 2px;
          font-size: 9px;
          letter-spacing: .12em;
          transition: .18s ease;
        }
        .azc-year:hover {
          color: var(--cyan-bright);
          border-bottom-color: var(--line-strong);
        }
        .azc-year-list {
          position: absolute;
          right: 0;
          top: 27px;
          z-index: 20;
          min-width: 74px;
          max-height: 170px;
          overflow-y: auto;
          padding: 4px;
          border: 1px solid var(--line-strong);
          border-radius: 7px;
          background: var(--surface-strong);
          box-shadow: 0 14px 35px rgba(0, 0, 0, .45), 0 0 18px rgba(69, 217, 255, .08);
          backdrop-filter: blur(14px);
        }
        .azc-year-item {
          display: block;
          width: 100%;
          padding: 6px 8px;
          border: 0;
          border-radius: 4px;
          background: transparent;
          color: var(--muted);
          cursor: pointer;
          text-align: right;
          font-size: 9px;
          transition: .15s ease;
        }
        .azc-year-item:hover,
        .azc-year-item.aktiv {
          color: var(--cyan-bright);
          background: rgba(69, 217, 255, .06);
        }
        .azc-heftegun {
          display: grid;
          grid-template-columns: repeat(7, 1fr);
          padding: 10px 12px 3px;
          color: #4f6975;
          text-align: center;
          font-size: 8px;
          font-weight: 500;
          letter-spacing: .1em;
        }
        .azc-gunler {
          display: grid;
          grid-template-columns: repeat(7, 1fr);
          padding: 3px 12px 13px;
        }
        .azc-hucre {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 32px;
        }
        .azc-gun {
          width: 27px;
          height: 27px;
          padding: 0;
          border: 1px solid transparent;
          border-radius: 50%;
          background: transparent;
          color: #9aabb2;
          cursor: pointer;
          font-size: 9px;
          transition: .16s ease;
        }
        .azc-gun:hover {
          color: var(--cyan-bright);
          border-color: var(--line-strong);
          background: rgba(69, 217, 255, .07);
          box-shadow: 0 0 12px rgba(69, 217, 255, .08);
        }
        .azc-gun.bugun {
          color: #021017;
          border-color: var(--cyan);
          background: var(--cyan);
          box-shadow: 0 0 15px rgba(69, 217, 255, .32);
          font-weight: 600;
        }
        @media (max-width: 900px) {
          .azc-top { grid-template-columns: 52px 1fr 52px; }
        }
      `}</style>

      <div className="azc-top">
        <div className="azc-nav">
          <button className="azc-navbtn" onClick={() => ayDeyis(-1)} aria-label="Əvvəlki ay">
            <FontAwesomeIcon icon={faChevronLeft} />
          </button>
          <button className="azc-navbtn" onClick={() => ayDeyis(1)} aria-label="Növbəti ay">
            <FontAwesomeIcon icon={faChevronRight} />
          </button>
        </div>
        <div className="azc-month">{AY_ADLARI[ay]}</div>
        <div className="azc-year-wrap">
          <button className="azc-year" onClick={() => setIlAcig(!ilAcig)} aria-expanded={ilAcig}>
            {il}
          </button>
          {ilAcig && (
            <div className="azc-year-list">
              {ilSiyahisi.map((y) => (
                <button
                  key={y}
                  className={`azc-year-item${y === il ? ' aktiv' : ''}`}
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
                <button className={`azc-gun${buGunMu ? ' bugun' : ''}`} aria-label={`${gun} ${AY_ADLARI[ay]} ${il}`}>
                  {gun}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
