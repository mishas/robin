import robin, stl
import os.path
robin.loadLibrary(__name__, os.path.normpath(__file__ + "/../libinheritance.so"))

IFunctor = robin.implement(IFunctor)