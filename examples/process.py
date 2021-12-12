import zipfile

from types import ModuleType
import sys
# from pathlib import Path
# file = Path(__ file __). resolve()
# package_root_directory = file.parents [1]
# sys.path.insert(0, '/tmp/process')



class MainCtrl:
    thread_continue = True
    # thread_token = "token"

main_ctrl = MainCtrl()

# python -m zipapp d -m 'lockd:main'
with zipfile.ZipFile("d.pyz", "r") as zip_ref:
  # zip_ref.extractall('/tmp/process')
  module = ModuleType("testmodule")
  context = module.__dict__.copy()
  # context['__package__'] = '.'
  # context['main_control'] = main_ctrl
  # context['__name__'] = '__main__'
  # print(context)
  for n in zip_ref.namelist():
    # print(n)
    if n == '__main__.py':
      continue
    # print(len(globals()))
    exec(zip_ref.read(n), context)
  # exec(zip_ref.read('__main__.py'), context)
  # print(context)
  context['main'](main_ctrl)

# with open('/tmp/process/__main__.py', 'r') as f:
#   context = module.__dict__.copy()
#   # context['__package__'] = '.'
#   context['main_control'] = object
#   # context['__name__'] = '__main__'
#   print(context)
#   exec(f.read(), context)
