EMAIL_TOOL_DECLARATIONS = [
    {
        "name": "get_emails",
        "description": (
            "Gmail hesabında email axtarır və uyğun mesajların göndərən, mövzu, tarix və qısa məzmununu qaytarır. "
            "Gmail axtarış sintaksisindən istifadə edə bilər: from:, to:, subject:, is:unread, after:, before:."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Gmail search query. Boş olarsa ən son mesajları qaytarır."
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum email sayı. Defolt 10."
                }
            }
        }
    },
    {
        "name": "read_email",
        "description": "Gmail-da message_id ilə konkret emaili oxuyur və məzmununu qaytarır."
        ,
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message_id": {
                    "type": "STRING",
                    "description": "Gmail message ID. get_emails nəticəsindən alınır."
                }
            },
            "required": ["message_id"]
        }
    }
]
