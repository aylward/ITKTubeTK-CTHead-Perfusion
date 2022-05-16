# -*- mode: python ; coding: utf-8 -*-

from glob import glob, iglob
from os import path
from PyInstaller import compat
from PyInstaller.utils.hooks import collect_submodules, get_package_paths

def gather_mkl_dlls():
    dlls = []
    pattern = path.join(compat.base_prefix, '**', '*.dll')
    for filename in iglob(pattern, recursive=True):
        basename = path.basename(filename)
        if basename.startswith('mkl_'):
            dlls.append((filename, '.'))
    return dlls

block_cipher = None

binaries = []

# for numpy
binaries += gather_mkl_dlls()

datas = []
datas += [('../lib/*.py', 'StroCoVess')]
datas += [('../lib/perfusion_toolbox/*.m', 'StroCoVess/perfusion_toolbox')]
datas += [('../lib/perfusion_toolbox/utils/*.m', 'StroCoVess/perfusion_toolbox/utils')]
datas += [('../lib/perfusion_toolbox/utils/*.mat', 'StroCoVess/perfusion_toolbox/utils')]
datas += [('../lib/perfusion_toolbox/utils/*.asv', 'StroCoVess/perfusion_toolbox/utils')]
datas += [('../lib/perfusion_toolbox/utils/*.fig', 'StroCoVess/perfusion_toolbox/utils')]
datas += [('../src/*.py', 'StroCoVess')]
datas += [('../src/atlas', 'StroCoVess/atlas')]
datas += [('../src/bin/*.exe', 'StroCoVess/bin')]

hiddenimports = ['site']

# ITK has a conditional torch dependency
excludes = ['torch']

hookspath = path.join(path.abspath(SPECPATH), 'hooks')

a = Analysis(['../src/StroCoVess_App.py'],
             pathex=[SPECPATH],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[hookspath],
             runtime_hooks=[],
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='StroCoVess_App',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='StroCoVess_App')
