import importlib


SAFE_MODULES = [
    "app_config",
    "memory.memory_manager",
    "actions.browser",
    "actions.calendar",
    "actions.media",
    "actions.open_app",
    "actions.reminders",
    "actions.shell",
    "actions.sys_info",
    "actions.tts",
    "actions.weather",
    "actions.whatsapp",
    "actions.youtube_stats",
    "tool_defs",
]


def test_safe_modules_import():
    for module_name in SAFE_MODULES:
        importlib.import_module(module_name)