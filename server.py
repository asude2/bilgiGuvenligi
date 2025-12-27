import socket
import sqlite3
import os
from PIL import Image
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad

# ########## DES FONKSİYONLARI (HAZIR KÜTÜPHANE) ##########
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

# ########## VERİTABANI HAZIRLIĞI ##########
def veritabani_hazirla():
    conn = sqlite3.connect("sistem.db")
    cursor = conn.cursor()
    # Kullanıcılar tablosu (Anahtar LSB'den gelecek)
    cursor.execute('''CREATE TABLE IF NOT EXISTS kullanicilar 
                      (id INTEGER PRIMARY KEY, kullanici_adi TEXT, anahtar TEXT)''')
    # Mesajlar tablosu (Mesajlar BLOB/Binary olarak saklanmalı çünkü DES çıktısı binarydir)
    cursor.execute('''CREATE TABLE IF NOT EXISTS mesajlar 
                      (id INTEGER PRIMARY KEY, gonderen TEXT, alici TEXT, mesaj BLOB)''')
    conn.commit()
    conn.close()

# ########## LSB ÇÖZME FONKSİYONU ##########
def resimden_sifre_coz(resim_yolu):
    img = Image.open(resim_yolu)
    pixels = list(img.getdata())
    binary_mesaj = ""
    for pixel in pixels:
        for i in range(3):
            binary_mesaj += str(pixel[i] & 1)
    veriler = [binary_mesaj[i:i+8] for i in range(0, len(binary_mesaj), 8)]
    mesaj = ""
    for byte in veriler:
        if byte == "11111111": break
        try:
            mesaj += chr(int(byte, 2))
        except: break
    return mesaj

# ########## SUNUCU ANA DÖNGÜSÜ ##########
def sunucuyu_baslat():
    veritabani_hazirla()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 12345))
    server.listen(5)
    print("--- Sunucu Aktif (DES ve LSB Destekli) ---")

    while True:
        baglanti, adres = server.accept()
        print(f"Bağlantı: {adres}")
        
        # Gelen ham veriyi al (Byte olarak alıyoruz çünkü mesaj şifreli gelecek)
        raw_data = baglanti.recv(4096)
        try:
            data = raw_data.decode('utf-8', errors='ignore')
        except:
            data = ""

        # 1. KAYIT KISMI
        if data.startswith("KAYIT"):
            k_adi = data.split("|")[1]
            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi=?", (k_adi,))
            if cursor.fetchone():
                baglanti.send("HATA|Kullanıcı adı alınmış".encode())
            else:
                baglanti.send("OK".encode())
                with open("gelen_resim.png", "wb") as f:
                    baglanti.settimeout(2.0)
                    try:
                        while True:
                            l = baglanti.recv(1024)
                            if not l: break
                            f.write(l)
                    except: pass
                
                cikarilan_sifre = resimden_sifre_coz("gelen_resim.png")
                cursor.execute("INSERT INTO kullanicilar (kullanici_adi, anahtar) VALUES (?, ?)", (k_adi, cikarilan_sifre))
                conn.commit()
                print(f"Kayıt Başarılı: {k_adi} (Anahtar: {cikarilan_sifre})")
            conn.close()

        # 2. GİRİŞ KISMI
        elif data.startswith("LOGIN"):
            parcalar = data.split("|")
            k_adi, girilen_sifre = parcalar[1], parcalar[2]
            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (k_adi,))
            sonuc = cursor.fetchone()
            
            if sonuc and sonuc[0] == girilen_sifre:
                cursor.execute("SELECT kullanici_adi FROM kullanicilar")
                liste = ",".join([k[0] for k in cursor.fetchall()])
                baglanti.send(f"BASARILI|{liste}".encode())
                print(f"Giriş: {k_adi}")
            else:
                baglanti.send("HATA|Hatalı şifre veya kullanıcı".encode())
            conn.close()

        # 3. MESAJ YÖNLENDİRME (DES ŞİFRELEME/DEŞİFRELEME BURADA)
        elif data.startswith("MESAJ_AT"):
            # Format: MESAJ_AT|gonderen|alici|SİFRELİ_BYTE_VERİ
            parcalar = data.split("|")
            gonderen, alici = parcalar[1], parcalar[2]
            
            # Verinin başlık kısmını atıp sadece şifreli byte kısmını alalım
            header_text = f"MESAJ_AT|{gonderen}|{alici}|"
            sifreli_payload = raw_data[len(header_text):]

            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            
            # ADIM 1: Gönderen kişinin anahtarıyla mesajı çöz
            cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (gonderen,))
            g_anahtar = cursor.fetchone()[0]
            try:
                cozulmus_mesaj = mesaj_coz_des(sifreli_payload, g_anahtar)
                print(f"Mesaj {gonderen} anahtarıyla çözüldü: {cozulmus_mesaj}")

                # ADIM 2: Alıcı kişinin anahtarıyla mesajı tekrar şifrele
                cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (alici,))
                a_anahtar = cursor.fetchone()[0]
                yeni_sifreli_mesaj = mesaj_sifrele_des(cozulmus_mesaj, a_anahtar)

                # ADIM 3: Alıcının kutusuna (Veritabanına) şifreli olarak kaydet
                cursor.execute("INSERT INTO mesajlar (gonderen, alici, mesaj) VALUES (?, ?, ?)", 
                               (gonderen, alici, yeni_sifreli_mesaj))
                conn.commit()
                print(f"Mesaj {alici} anahtarıyla tekrar şifrelendi ve veritabanına kaydedildi.")
            except Exception as e:
                print(f"DES İşlem Hatası: {e}")
            conn.close()

        # 4. MESAJLARI ÇEKME KISMI
        elif data.startswith("MESAJLARI_GETIR"):
            k_adi = data.split("|")[1]
            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            # Bu kullanıcıya gelen mesajları bul
            cursor.execute("SELECT gonderen, mesaj FROM mesajlar WHERE alici=?", (k_adi,))
            mesajlar = cursor.fetchall()
            
            # Mesajları 'gonderen:mesaj_byte' formatında birleştirip gönder
            yanit = ""
            for m in mesajlar:
                # m[1] (mesaj) binary olduğu için hex formatına çevirip yolluyoruz
                yanit += f"{m[0]}:{m[1].hex()}|"
            
            baglanti.send(yanit.encode() if yanit else "MESAJ_YOK".encode())
            conn.close()

        baglanti.close()

if __name__ == "__main__":
    sunucuyu_baslat()