TASK_TOOL_DECLARATIONS = [
    {
        "name": "update_reminder",
        "description": "Google Tasks-da mövcud tapşırığı yeniləyir. Başlıq, son tarix və ya qeyd dəyişdirilə bilər.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task_id": {"type": "STRING", "description": "Google Tasks task ID"},
                "title": {"type": "STRING", "description": "Yeni başlıq"},
                "due_iso": {"type": "STRING", "description": "Yeni son tarix/saat, ISO formatında"},
                "notes": {"type": "STRING", "description": "Yeni qeyd"},
                "list_name": {"type": "STRING", "description": "Task siyahısının adı"},
                "all_day": {"type": "BOOLEAN", "description": "Son tarix bütün gün üçündürsə true"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "complete_reminder",
        "description": "Google Tasks-da tapşırığı tamamlandı kimi işarələyir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task_id": {"type": "STRING", "description": "Google Tasks task ID"},
                "list_name": {"type": "STRING", "description": "Task siyahısının adı"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "delete_reminder",
        "description": "Google Tasks-dan konkret tapşırığı silir. İstifadəçidən silmə təsdiqi alınmadan çağırılmamalıdır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task_id": {"type": "STRING", "description": "Google Tasks task ID"},
                "list_name": {"type": "STRING", "description": "Task siyahısının adı"},
            },
            "required": ["task_id"],
        },
    },
]
