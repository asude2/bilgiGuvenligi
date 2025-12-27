from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad

def mesaj_sifrele_des(mesaj, anahtar):
    # Anahtarı tam 8 byte yap (DES kuralı)
    anahtar_8 = anahtar.ljust(8)[:8].encode('utf-8')
    cipher = DES.new(anahtar_8, DES.MODE_ECB)
    # Mesajı blok boyutuna (8 byte) tamamla ve şifrele
    sifreli_byte = cipher.encrypt(pad(mesaj.encode('utf-8'), 8))
    return sifreli_byte

def mesaj_coz_des(sifreli_byte, anahtar):
    anahtar_8 = anahtar.ljust(8)[:8].encode('utf-8')
    cipher = DES.new(anahtar_8, DES.MODE_ECB)
    # Şifreyi çöz ve tamamlamayı (padding) kaldır
    cozulmus_mesaj = unpad(cipher.decrypt(sifreli_byte), 8)
    return cozulmus_mesaj.decode('utf-8')
    
anahtar = "gizli123" # 8 karakter
mesaj = "Selam C2, bu bir gizli mesajdir."

sifreli = mesaj_sifrele_des(mesaj, anahtar)
print(f"Şifreli (Okunamaz): {sifreli}")

cozulmus = mesaj_coz_des(sifreli, anahtar)
print(f"Çözülmüş (Okunabilir): {cozulmus}")