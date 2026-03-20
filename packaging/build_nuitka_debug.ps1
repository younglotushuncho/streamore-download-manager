
$ErrorActionPreference = 'Stop'
Write-Host "Running Nuitka Build with Verbose Logging..." -ForegroundColor Cyan

# Use the exact same command as build_nuitka.ps1 but with --verbose and --show-scons
python -m nuitka --standalone --mingw64 `
    --windows-disable-console `
    --output-dir="dist" `
    --windows-icon-from-ico="desktop\icon.ico" `
    --enable-plugin=pyqt6 `
    --include-data-dir="bin=bin" `
    --include-package="backend" `
    --include-package="shared" `
    --include-module="sqlite3" `
    --include-module="engineio.async_drivers.threading" `
    --include-module="flask_socketio" `
    --include-module="flask_cors" `
    --include-module="simple_websocket" `
    --include-module="pystray._win32" `
    --include-module="PIL._tkinter_finder" `
    --include-module="plyer.platforms.win.notification" `
    --include-module="curl_cffi" `
    --include-module="bs4" `
    --nofollow-import-to="PIL.BlpImagePlugin" `
    --nofollow-import-to="PIL.BufrStubImagePlugin" `
    --nofollow-import-to="PIL.CurImagePlugin" `
    --nofollow-import-to="PIL.DcxImagePlugin" `
    --nofollow-import-to="PIL.DdsImagePlugin" `
    --nofollow-import-to="PIL.EpsImagePlugin" `
    --nofollow-import-to="PIL.FliImagePlugin" `
    --nofollow-import-to="PIL.FpxImagePlugin" `
    --nofollow-import-to="PIL.FtexImagePlugin" `
    --nofollow-import-to="PIL.GbrImagePlugin" `
    --nofollow-import-to="PIL.GribStubImagePlugin" `
    --nofollow-import-to="PIL.Hdf5StubImagePlugin" `
    --nofollow-import-to="PIL.IcnsImagePlugin" `
    --nofollow-import-to="PIL.ImtImagePlugin" `
    --nofollow-import-to="PIL.IptcImagePlugin" `
    --nofollow-import-to="PIL.McIdasImagePlugin" `
    --nofollow-import-to="PIL.MicImagePlugin" `
    --nofollow-import-to="PIL.MpegImagePlugin" `
    --nofollow-import-to="PIL.MspImagePlugin" `
    --nofollow-import-to="PIL.PalmImagePlugin" `
    --nofollow-import-to="PIL.PcdImagePlugin" `
    --nofollow-import-to="PIL.PdfImagePlugin" `
    --nofollow-import-to="PIL.PixarImagePlugin" `
    --nofollow-import-to="PIL.SgiImagePlugin" `
    --nofollow-import-to="PIL.SpiderImagePlugin" `
    --nofollow-import-to="PIL.SunImagePlugin" `
    --nofollow-import-to="PIL.TgaImagePlugin" `
    --nofollow-import-to="PIL.WmfImagePlugin" `
    --nofollow-import-to="PIL.XVThumbImagePlugin" `
    --nofollow-import-to="PIL.XbmImagePlugin" `
    --nofollow-import-to="PIL.XpmImagePlugin" `
    --lto=yes `
    --output-filename="StreamoreManager.exe" `
    --jobs=4 `
    --verbose `
    --show-scons `
    desktop\downloader_app.py 2>&1 | Tee-Object -FilePath "nuitka_debug.log"
