"""WhatsApp read tool declarations."""

WHATSAPP_TOOL_DECLARATIONS = [
    {
        "name": "read_whatsapp_conversations",
        "description": (
            "WhatsApp Web-də görünən söhbətləri oxuyur. "
            "İstifadəçi WhatsApp söhbətləri, çat siyahısı və ya kimlərlə yazışdığını soruşduqda istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
    {
        "name": "read_whatsapp_messages",
        "description": (
            "WhatsApp Web-də hazırda görünən yeni mesajları oxuyur. "
            "İstifadəçi WhatsApp mesajlarını, yeni gələn mesajları və ya oxunmalı WhatsApp yazışmalarını soruşduqda istifadə et. "
            "Nəticə strukturlaşdırılmış mesaj məlumatıdır: id, conversation_id, sender, timestamp, direction və content."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        },
    },
]
