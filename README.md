# E.V.A

E.V.A Windows mühitində işləyən, Gemini Live API əsaslı real vaxtlı səsli şəxsi AI köməkçisidir.

## Əsas imkanlar

- Real vaxtlı səsli söhbət
- Yazılı komanda daxil etmə
- Tətbiq açma və sistem məlumatları
- Təhlükəsiz shell əmrlərinin icrası
- Hava məlumatı
- Ekran analizi
- Webcam görüntüsünün canlı ötürülməsi
- Media və YouTube idarəsi
- YouTube kanal hesabatı
- WhatsApp mesajları və kontakt yaddaşı
- Davamlı yaddaş
- Google Calendar inteqrasiyası
- Xatırladıcılarla işləmə

## Quraşdırma

Python 3.10 və ya daha yeni versiya tələb olunur.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Başlatma

```powershell
python main.py
```

Windows üçün `BASLAT.bat` faylından da istifadə etmək mümkündür.

## Google Calendar

Google Calendar real Google Calendar API ilə işləyir. OAuth prosesi ilk qoşulmada tamamlanır.

Dəstəklənən əməliyyatlar:

- Tədbirləri oxuma
- Yeni tədbir yaratma
- Tədbir silmə

İnteqrasiyanın əsas faylları:

```text
integrations/google/auth.py
integrations/google/calendar.py
```

OAuth tokeni lokal olaraq aşağıdakı faylda saxlanılır:

```text
config/google_token.json
```

Bu fayl məxfi məlumat ehtiva edir və Git repository-yə commit edilməməlidir.

## Layihə strukturu

```text
core/          əsas runtime modulları və təhlükəsizlik
integrations/  xarici xidmət inteqrasiyaları
actions/       EVA əməliyyatları
memory/        yaddaş sistemi
tests/         testlər
main.py        tətbiqin əsas orkestrasiya axını
```

## Testlər

```powershell
python -m pytest -q
```

Hazırkı test dəsti 46 testdən ibarətdir.

Sintaksis yoxlaması:

```powershell
python -m compileall main.py core integrations actions tests
```

## Windows qeydləri

Webcam və ekran funksiyaları üçün Windows məxfilik icazələri tələb oluna bilər:

`Settings → Privacy & security → Camera`

Ətraflı Windows istifadə təlimatı üçün `OKU_BENI.txt` faylına bax.
