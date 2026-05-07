import py_compile
py_compile.compile('backend/app/ml/model.py', doraise=True)
py_compile.compile('backend/app/ml/preprocessing.py', doraise=True)
print('compiled')
