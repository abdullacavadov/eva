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
        "name": "read_email_thread",
        "description": (
            "Gmail thread-dəki bütün mesajları oxuyur. "
            "thread_id əvvəlki email nəticəsindən alınmalıdır."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "thread_id": {
                    "type": "STRING",
                    "description": "Gmail thread ID."
                }
            },
            "required": ["thread_id"]
        }
    },
    {
        "name": "prepare_email_reply",
        "description": (
            "Mövcud Gmail emailinə cavab hazırlayır və Gmail Draft yaradır. "
            "Email göndərilmir. Nəticə istifadəçiyə göstərilib təsdiq tələb edir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message_id": {
                    "type": "STRING",
                    "description": "Cavab veriləcək Gmail message ID."
                },
                "body": {
                    "type": "STRING",
                    "description": "Hazırlanmış cavab mətni."
                }
            },
            "required": ["message_id", "body"]
        }
    },
    {
        "name": "prepare_new_email",
        "description": (
            "Yeni Gmail emaili hazırlayır və Draft yaradır. "
            "Email göndərilmir. İstifadəçi təsdiqindən sonra send_email istifadə olunur."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {
                    "type": "STRING",
                    "description": "Recipient email ünvanı."
                },
                "subject": {
                    "type": "STRING",
                    "description": "Email mövzusu."
                },
                "body": {
                    "type": "STRING",
                    "description": "Email mətni."
                },
                "cc": {
                    "type": "STRING",
                    "description": "İstəyə bağlı CC."
                },
                "bcc": {
                    "type": "STRING",
                    "description": "İstəyə bağlı BCC."
                }
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "send_email",
        "description": (
            "Əvvəlcədən hazırlanmış Gmail Draft-ı göndərir. "
            "Yalnız istifadəçi həmin draftın göndərilməsini açıq şəkildə təsdiqlədikdən sonra istifadə et."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "draft_id": {
                    "type": "STRING",
                    "description": "İstifadəçinin təsdiqlədiyi Gmail draft ID."
                }
            },
            "required": ["draft_id"]
        }
    },
    {
        "name": "read_email",
        "description": "Gmail-da message_id ilə konkret emaili oxuyur və məzmununu qaytarır.",
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
    },
    {
        "name": "sync_google_contacts",
        "description": (
            "Google Contacts-dakı kontaktları local phone_book.json ilə sinxronizasiya edir. "
            "Yalnız istifadəçi açıq şəkildə 'kontaktları sinxronizasiya et' və ya ekvivalent əmr verdikdə istifadə et. "
            "WhatsApp mesajı göndərərkən bu aləti avtomatik çağırma. "
            "Google Contacts-dan yalnız oxuyur; Google kontakt yaratmır, dəyişmir və silmir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    }
]
