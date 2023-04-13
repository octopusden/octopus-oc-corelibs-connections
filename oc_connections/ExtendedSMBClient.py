import warnings
warnings.simplefilter("always")
warnings.warn("ExtendedSMBClient has been deprecated. Please consider get rid of using it.", ImportWarning)

from sys import version_info
if version_info.major == 3:
    raise ImportError("CDT SaMBa support are not ported to python 3. Please do not use it.")

from cdt.vfs import SMBClient

class ExtendedSMBClient(SMBClient.SMBClient):
    """ copied from mirror/check.py"""

    def recurse(self,path='',depth=-1):
        """recurse directories with limited depth"""
        if depth == 0: return []
        if path[-1] != '/': path += '/'
        result = []
        for d in self.ls(path):
            d = d.lstrip('/')
            if d == path: continue
            if d[-1] == '/': result.extend(self.recurse(d,depth-1))
            result.append(d)
        return result
