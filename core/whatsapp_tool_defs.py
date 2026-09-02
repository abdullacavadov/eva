"""WhatsApp read and Business Cloud API tool declarations."""

WHATSAPP_TOOL_DECLARATIONS = [
    {
        "name": "read_whatsapp_conversations",
        "description": "WhatsApp Web-də görünən söhbətləri oxuyur. İstifadəçi WhatsApp söhbətləri, çat siyahısı və ya kimlərlə yazışdığını soruşduqda istifadə et.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "read_whatsapp_messages",
        "description": "WhatsApp Web-də görünən yeni mesajları oxuyur. conversation veriləndə həmin söhbəti açıb mesajları oxuyur.",
        "parameters": {"type": "OBJECT", "properties": {"conversation": {"type": "STRING", "description": "İxtiyari söhbət adı və ya conversation identifikatoru."}}},
    },
    {
        "name": "send_whatsapp_business_message",
        "description": "Meta WhatsApp Business Cloud API ilə mətn mesajı göndərir. Yalnız WhatsApp Business Cloud credentials konfiqurasiya olunubsa istifadə et və göndərişdən əvvəl açıq istifadəçi təsdiqi al.",
        "parameters": {"type": "OBJECT", "properties": {"phone_number": {"type": "STRING", "description": "Beynəlxalq telefon nömrəsi, məsələn +99450xxxxxxx"}, "message": {"type": "STRING", "description": "Göndəriləcək mətn"}, "confirmation_id": {"type": "STRING", "description": "Açıq təsdiqdən sonra verilən identifikator"}}, "required": ["phone_number", "message"]},
    },
]
