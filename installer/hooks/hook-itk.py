import site
from os import path
from PyInstaller.utils.hooks import get_package_paths

def from_site(filename):
    for sitepath in site.getsitepackages():
        if path.exists(path.join(sitepath, filename)):
            return path.join(sitepath, filename)
    raise Exception(f'{filename} not found')

_, pkgpath = get_package_paths('itk')


datas = [
    (path.join(pkgpath, 'Configuration'), path.join('itk', 'Configuration')),
    (path.join(pkgpath, '*.py'), 'itk'),
    (path.join(pkgpath, '*.pyd'), 'itk'),
]

binaries = []
    #(path.join(from_site('itk_core.libs'), '*.dll'), 'itk_core.libs'),
#]
