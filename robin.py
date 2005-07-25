import imp, os.path, __builtin__

libdir = os.path.dirname(__file__)
machine = os.uname()[0] #os.environ["MACHINE"]
model = ["RELEASE", "DEBUG"][os.environ.has_key("ROBIN_DEBUG")]
soext = "TODO: autoconf"

if machine == "win32":
	target = "lib/%s/%s/robin_pyfe%s"
else:
	target = "lib/%s/%s/librobin_pyfe%s"

target = target % (model, machine, soext)
target = "librobin_pyfe.dll"
imp.load_dynamic("robin", os.path.join(libdir, target))
__builtin__.double = double
__builtin__.char = char
__builtin__.ulong = ulong
__builtin__.uint = uint
__builtin__.uchar = uchar

ldinfo = { 'm': machine, 'so': soext, \
           'suffix': "", 'confdir': "." }

def here(file):
	import os
	if file.endswith(".pyc") and os.path.isfile(file[:-1]):
		file = file[:-1]
	return os.path.dirname(os.path.realpath(file)) 


# Cleanup
del imp, os, libdir, target, __builtin__