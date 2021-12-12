import zipfile

# python -m zipapp d -m 'lockd:main'
with zipfile.ZipFile("d.pyz", "r") as zip_ref:
  context = {'main_control': object}
  for n in zip_ref.namelist():
    print(n)
    if n == '__main__.py':
      continue
    print(len(globals()))
    exec(zip_ref.read(n))
  exec(zip_ref.read('__main__.py'))
