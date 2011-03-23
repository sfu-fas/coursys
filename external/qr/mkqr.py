from PyQRNative import *

qr = QRCode(2, QRErrorCorrectLevel.L)
qr.addData("https://courses.cs.sfu.ca/m/")
qr.make()
im = qr.makeImage()

im.save("qr.png")
