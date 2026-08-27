"""Legacy UI compatibility shim.

EVA-nın real UI-si artıq React-dir. Tkinter əsaslı köhnə desktop UI bu moduldan
çıxarılıb; mövcud backend import-larını qırmamaq üçün yalnız RuntimeUI aliası
saxlanılır.
"""

from core.runtime_ui import RuntimeUI

JarvisUI = RuntimeUI

__all__ = ["JarvisUI", "RuntimeUI"]
