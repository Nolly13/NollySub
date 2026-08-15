#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Net-Rip -> NollySub yönlendirme modülü.
"""
import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    nollysub_script = Path(__file__).parent / "nollysub.py"
    if nollysub_script.exists():
        subprocess.run([sys.executable, str(nollysub_script)] + sys.argv[1:])
    else:
        print("Hata: nollysub.py dosyası bulunamadı.")
