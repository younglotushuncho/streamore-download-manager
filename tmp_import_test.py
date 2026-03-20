import traceback, sys
try:
    import frontend.ui.movie_details as m
    print('imported successfully')
except Exception:
    traceback.print_exc()
    sys.exit(1)
