import board
import busio
from adafruit_pn532.i2c import PN532_I2C

# Inicializar el bus I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Inicializar el PN532
pn532 = PN532_I2C(i2c, debug=False)

# Verificar que el chip responde
ic, ver, rev, support = pn532.firmware_version
print(f"PN532 detectado — firmware v{ver}.{rev}")

# Configurar para leer tags NFC
pn532.SAM_configuration()

print("Esperando un tag NFC... (acercá un disco)")

while True:
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is not None:
        uid_str = ":".join([format(b, "02X") for b in uid])
        print(f"Tag detectado — UID: {uid_str}")
