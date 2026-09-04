"""
EVA — Gemini Live alət tərifləri.
Windows masaüstü nüvəsi (main.py) tərəfindən istifadə olunur.
"""

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Windows-da istənilən tətbiqi açır. Spotify, Chrome, Terminal, Fayl Explorer, VS Code və s.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Tətbiqin adı (məsələn, 'Spotify', 'Chrome', 'Terminal')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "sys_info",
        "description": "Sistem məlumatlarını alır: batareya vəziyyəti, CPU, RAM, disk, saat, tarix və şəbəkə bağlantısı. Həmçinin Windows səs səviyyəsini və ekran parlaqlığını oxuya və artırıb-azalda bilər; volume/volume_up/volume_down/brightness/brightness_up/brightness_down sorğularından istifadə et.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "battery | cpu | ram | disk | time | date | network | all"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": (
            "Cari hava vəziyyətini ümumiləşdirir. Defolt məkan Bakı-dur. "
            "İstifadəçi hava vəziyyəti, temperatur və ya yağış barədə soruşduqda istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "Şəhər və ya məkan. Boş saxlanılarsa Bakı istifadə olunur."
                }
            }
        }
    },
    {
        "name": "get_calendar_events",
        "description": (
            "Google Calendar tədbirlərini oxuyur. "
            "Bu gün, sabah, növbəti tədbir və ya yaxın gündəliyi ümumiləşdirir. "
            "İstifadəçi görüş, təqvim, gündəlik, tədbir və ya günün proqramı barədə soruşduqda istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "today | tomorrow | next | agenda | week və ya təbii dildə "
                        "'növbəti 30 gün', '2 həftə', 'bu ay', 'gələn ay'"
                    )
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum tədbir sayı"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_calendar_event",
        "description": (
            "Google Calendar-a yeni tədbir əlavə edir. "
            "İstifadəçi görüş, randevu, təqvimə əlavə etmə və ya tədbir yaratmağı istədikdə istifadə et. "
            "Başlanğıc tarixini real tarix və saat kimi ver; bitiş verilməzsə defolt müddətdən istifadə olunur."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Tədbirin başlığı. Məsələn: 'Diş həkimi randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Başlanğıc tarix/saatı. ISO və ya yyyy-MM-dd HH:mm formatında."
                },
                "end_iso": {
                    "type": "STRING",
                    "description": "Bitiş tarix/saatı. İxtiyaridir."
                },
                "location": {
                    "type": "STRING",
                    "description": "Tədbirin məkanı. İxtiyaridir."
                },
                "notes": {
                    "type": "STRING",
                    "description": "Tədbir qeydləri. İxtiyaridir."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Əlavə ediləcək təqvimin adı. İxtiyaridir."
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "true olarsa bütün gün davam edən tədbir yaradır."
                }
            },
            "required": ["title", "start_iso"]
        }
    },
    {
        "name": "delete_calendar_event",
        "description": (
            "Google Calendar-dan tədbir silir. "
            "İstifadəçi görüşü, randevunu və ya təqvim qeydini silmək istədikdə istifadə et. "
            "Eyni adlı bir neçə tədbir varsa düzgün qeydi tapmaq üçün başlanğıc tarixini real tarix və saat kimi ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Silinəcək tədbirin başlığı. Məsələn: 'Diş həkimi randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "İxtiyari tarix/saat. Eyni adlı bir neçə tədbiri ayırmaq üçün istifadə olunur."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "İxtiyari təqvim adı"
                },
                "delete_all_matches": {
                    "type": "BOOLEAN",
                    "description": "true olarsa uyğun gələn bütün tədbirləri silir"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "get_reminders",
        "description": (
            "Microsoft To-Do xatırlatmalar siyahısını oxuyur. "
            "Bu günkü, yaxınlaşan, gecikmiş və ya bütün açıq xatırlatmaları ümumiləşdirir. "
            "İstifadəçi xatırlatma, görüləcək işlər və ya tapşırıqlar siyahısı barədə soruşduqda istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "today | upcoming | overdue | all | next"
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum xatırlatma sayı"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "İstənilərsə konkret xatırlatma siyahısının adı"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_reminder",
        "description": (
            "Microsoft To-Do tətbiqinə yeni xatırlatma əlavə edir. "
            "İstifadəçi 'xatırlat', 'xatırlatma əlavə et', 'xatırlatma qur' dedikdə istifadə et. "
            "Nisbi vaxt ifadələrini cari tarix kontekstinə əsasən due_iso sahəsində ISO formatına çevir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Xatırlatmanın başlığı"
                },
                "due_iso": {
                    "type": "STRING",
                    "description": "İxtiyari tarix/saat. Məsələn: 2026-04-13T09:00 və ya bütün gün üçün 2026-04-13"
                },
                "notes": {
                    "type": "STRING",
                    "description": "İxtiyari qeyd"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "İxtiyari xatırlatma siyahısı"
                },
                "priority": {
                    "type": "STRING",
                    "description": "low | medium | high"
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "Bütün gün xatırlatmasıdırsa true"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "browser_control",
        "description": "Brauzerdə URL açır, Google-da axtarış edir, YouTube-da ilk nəticəni oynadır və iki məkan arasında Google Maps marşrutunu canlı trafik xəritəsi ilə açır. action: open_url | search | play_youtube | traffic; traffic üçün query-də başlanğıc -> təyinat ver.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open_url | search | play_youtube"},
                "url":    {"type": "STRING", "description": "Açılacaq URL (open_url üçün)"},
                "query":  {"type": "STRING", "description": "Axtarış sorğusu (search və ya play_youtube üçün)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "shell_run",
        "description": "Windows əmr sətrində (cmd.exe) komanda icra edir. Fayl əməliyyatları və sistem idarəetməsi üçün istifadə olunur.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "İcra ediləcək komanda"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "toggle_webcam",
        "description": (
            "Real vaxtda veb-kamera axınını başladır və ya dayandırır. "
            "Axın aktiv olduqda model davamlı kamera görüntüsü alır — 'bax', 'gör', 'göstər', "
            "'kameraya bax', 'qarşımdakını izah et', 'nə görürsən' kimi əmrlərdə 'start' istifadə et. "
            "'kameranı söndür', 'artıq baxma' kimi hallarda 'stop' istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "start — axını başlat  |  stop — axını dayandır"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "play_media",
        "description": (
            "YouTube və ya Spotify-da mahnı, musiqi və ya video açır. "
            "İstifadəçi konkret platforma deyərsə ondan istifadə et. "
            "Platforma bildirilməzsə uyğun olanı sına. "
            "İstifadəçi 'çal', 'oynat', 'aç' deyirsə autoplay=true istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Mahnı, ifaçı, albom və ya video axtarış ifadəsi"
                },
                "provider": {
                    "type": "STRING",
                    "description": "auto | youtube | spotify"
                },
                "autoplay": {
                    "type": "BOOLEAN",
                    "description": "true olarsa mümkün olduqda birbaşa oynadır"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_youtube_channel_report",
        "description": (
            "YouTube kanalının açıq statistikasını və son videoların performansını hesabat şəklində təqdim edir. "
            "İstifadəçi kanal statistikası, abunəçi sayı, son videolar, böyümə sürəti və ya YouTube analitikası barədə soruşduqda istifadə et. "
            "Bu alət Studio əvəzinə açıq YouTube Data API məlumatlarından istifadə edir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Təbii dildə analiz sorğusu. Məsələn: "
                        "'YouTube statistikalarım necədir', 'son videolarımı analiz et', "
                        "'kanal böyüməmi ümumiləşdir'"
                    )
                },
                "handle": {
                    "type": "STRING",
                    "description": (
                        "İxtiyari kanal handle-ı, kanal linki və ya kanal ID-si. "
                        "Boş saxlanılarsa ayarlardakı youtube_channel_handle istifadə olunur."
                    )
                },
                "video_limit": {
                    "type": "NUMBER",
                    "description": "Analizə daxil ediləcək son video sayı. Defolt 6."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_screen",
        "description": (
            "Aktiv pəncərənin ekran görüntüsünü alır və Gemini vision ilə analiz edir. "
            "İstifadəçi ekranda nə olduğunu, xətanı, görünən mətni, düymələri və ya pəncərə məzmununu soruşduqda istifadə et. "
            "Bu versiya yalnız aktiv pəncərəni dəstəkləyir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "İstifadəçinin ekranla bağlı sualı. Məsələn: 'Bu xətanı oxu', 'Ekranda nə var?'"
                },
                "target": {
                    "type": "STRING",
                    "description": "Hazırda yalnız active_window dəstəklənir."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "save_memory",
        "description": "İstifadəçi haqqında vacib məlumatı daimi yaddaşa yazır. Ad, seçimlər, layihələr və s. eşidildikdə səssizcə çağır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "identity | preferences | projects | notes"
                },
                "key":   {"type": "STRING", "description": "Qısa açar (məsələn, 'name')"},
                "value": {"type": "STRING", "description": "Dəyər (İngilis dilində)"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "delete_memory",
        "description": (
            "Daimi yaddaşdakı qeydi silir. "
            "İstifadəçi 'bunu yaddaşından sil', 'unut', 'sil' kimi əmr verdikdə istifadə et. "
            "Mümkündürsə category və key ilə sil; əmin deyilsənsə match_text ilə əlaqəli qeydi tapıb sil."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Qeydin kateqoriyası. Məsələn: notes | identity | preferences | projects"
                },
                "key": {
                    "type": "STRING",
                    "description": "Silinəcək açar. Məsələn: claude_limit_refresh"
                },
                "match_text": {
                    "type": "STRING",
                    "description": "Qeydi tapmaq üçün istifadə ediləcək təbii dil hissəsi. Məsələn: 'claude ai limit yenilənməsi'"
                }
            }
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": (
            "WhatsApp Desktop və ya WhatsApp Web üzərindən mesaj qaralamasını açır və ya mesajı göndərir. "
            "Kontakt adı və ya telefon nömrəsi ilə işləyə bilər. "
            "Telefon nömrəsi verilməyibsə əvvəlcə adı yadda saxlanılmış WhatsApp kontaktlarında və idxal edilmiş telefon kitabçasında axtar. "
            "İstifadəçi 'göndər', 'yolla', 'ilə', 'indi göndər' kimi açıq göndərmə niyyəti bildirirsə əlavə təsdiq istəmədən send_now=true istifadə et. "
            "Yalnız 'hazırla', 'qaralama aç', 'yaz, amma göndərmə' deyirsə send_now=false istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient_name": {
                    "type": "STRING",
                    "description": "Kontaktın adı. Məsələn: 'Ana', 'Əhməd', 'Ece'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Beynəlxalq telefon nömrəsi. Məsələn: +905551112233"
                },
                "message": {
                    "type": "STRING",
                    "description": "Göndəriləcək mesajın məzmunu"
                },
                "app_target": {
                    "type": "STRING",
                    "description": "desktop | web | auto. Defolt auto, üstünlük desktop."
                },
                "send_now": {
                    "type": "BOOLEAN",
                    "description": "true olarsa söhbət açıldıqdan sonra mesajı avtomatik göndərir"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "save_whatsapp_contact",
        "description": (
            "Tez-tez istifadə olunan WhatsApp kontaktını adı və telefon nömrəsi ilə daimi yaddaşa yazır. "
            "İstifadəçi bir şəxsi 'anam', 'Əhməd', 'iş ortağım' kimi gələcəkdə istifadə ediləcək formada təyin etdikdə istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {
                    "type": "STRING",
                    "description": "Yadda saxlanılacaq kontakt adı. Məsələn: 'Anam', 'Əhməd'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Beynəlxalq telefon nömrəsi. Məsələn: +905551112233"
                },
                "aliases": {
                    "type": "STRING",
                    "description": "Vergüllə ayrılmış alternativ müraciətlər. Məsələn: 'ana, anam, mom'"
                }
            },
            "required": ["display_name", "phone_number"]
        }
    }
]
