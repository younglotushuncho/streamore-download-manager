import os,sys
binp = os.path.join(sys.prefix, 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin')
print('dll dir:', binp, 'exists=', os.path.exists(binp))
if os.path.exists(binp):
    os.add_dll_directory(binp)
try:
    import PyQt6.QtCore as QC
    print('PyQt6.QtCore imported OK:', QC)
except Exception as e:
    print('Import failed:', repr(e))
    import traceback
    traceback.print_exc()
