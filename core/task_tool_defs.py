import tool_defs as _tool_defs

# Agenda flow replaces the legacy add_reminder declaration in tool_defs.py.
_tool_defs.TOOL_DECLARATIONS[:] = [item for item in _tool_defs.TOOL_DECLARATIONS if item.get("name") != "add_reminder"]
for _item in _tool_defs.TOOL_DECLARATIONS:
    if _item.get("name") == "get_reminders":
        _item["description"] = (
            "Google Tasks tapşırıqlar siyahısını oxuyur. "
            "Bu günkü, yaxınlaşan və ya açıq tapşırıqları ümumiləşdirir. "
            "İstifadəçi xatırlatma, görüləcək işlər və ya tapşırıqlar siyahısı barədə soruşduqda istifadə et."
        )

TASK_TOOL_DECLARATIONS = [
    {
        "name": "update_reminder",
        "description": "Google Tasks-da mövcud tapşırığı yeniləyir. Başlıq, son tarix və ya qeyd dəyişdirilə bilər.",
        "parameters": {"type": "OBJECT", "properties": {"task_id": {"type": "STRING", "description": "Google Tasks task ID"}, "title": {"type": "STRING", "description": "Yeni başlıq"}, "due_iso": {"type": "STRING", "description": "Yeni son tarix/saat, ISO formatında"}, "notes": {"type": "STRING", "description": "Yeni qeyd"}, "list_name": {"type": "STRING", "description": "Task siyahısının adı"}, "all_day": {"type": "BOOLEAN", "description": "Son tarix bütün gün üçündürsə true"}}, "required": ["task_id"]},
    },
    {
        "name": "complete_reminder",
        "description": "Google Tasks-da tapşırığı tamamlandı kimi işarələyir.",
        "parameters": {"type": "OBJECT", "properties": {"task_id": {"type": "STRING", "description": "Google Tasks task ID"}, "list_name": {"type": "STRING", "description": "Task siyahısının adı"}}, "required": ["task_id"]},
    },
    {
        "name": "delete_reminder",
        "description": "Google Tasks-dan konkret tapşırığı silir. Silmə təsdiqi tələb olunur.",
        "parameters": {"type": "OBJECT", "properties": {"task_id": {"type": "STRING", "description": "Google Tasks task ID"}, "list_name": {"type": "STRING", "description": "Task siyahısının adı"}}, "required": ["task_id"]},
    },
    {
        "name": "get_daily_agenda",
        "description": "Bu gün üçün Google Calendar, Google Tasks və EVA memory-də saxlanmış agenda qeydlərini vahid nəticədə oxuyur.",
        "parameters": {"type": "OBJECT", "properties": {"limit": {"type": "NUMBER", "description": "Maksimum nəticə sayı"}}},
    },
    {
        "name": "add_agenda_item",
        "description": "Task və ya qeyd əlavə edir. İstifadəçi harada yadda saxlanacağını deməyibsə əvvəlcə seçim soruş: Google Tasks və ya EVA yaddaşı. Google Tasks qoşulu deyilsə avtomatik EVA yaddaşına fallback et.",
        "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING", "description": "Task və ya qeydin başlığı"}, "item_type": {"type": "STRING", "description": "task | note"}, "storage": {"type": "STRING", "description": "google_tasks | memory; istifadəçi seçim etməyibsə boş saxla"}, "due_iso": {"type": "STRING", "description": "İxtiyari son tarix/saat, ISO formatında"}, "notes": {"type": "STRING", "description": "İxtiyari qeyd"}}, "required": ["title"]},
    },
    {
        "name": "delete_agenda_item",
        "description": "Task və ya qeydi silir. İstifadəçi yalnız memory deyirsə yalnız memory-də axtar. Tarix/saat verilibsə uyğun qeydi seç. Bir neçə uyğunluqda silmə etmir; istifadəçidən dəqiq seçim və açıq təsdiq tələb edir.",
        "parameters": {"type": "OBJECT", "properties": {"match_text": {"type": "STRING", "description": "Silinəcək task və ya qeyd"}, "storage": {"type": "STRING", "description": "google_tasks | memory; boş olarsa hər iki aktiv provider-də axtar"}, "confirm": {"type": "BOOLEAN", "description": "İstifadəçi açıq şəkildə təsdiq edibsə true"}}, "required": ["match_text"]},
    },
]
