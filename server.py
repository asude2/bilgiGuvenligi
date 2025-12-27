import socket  #pythonun ağ iletişimi için kullandığı kütüph.
import sqlite3
import os #dosya işl. yönetmek için
from PIL import Image #resmi LSB ile çözmek için
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad
import base64

                   ###########  DES ALGORİTMASI (ŞİFRELEME/ÇÖZME) ###############
def des_sifrele(mesaj,anahtar):
    anahtar_8mb=anahtar.ljust(8)[:8].encode('utf-8')  #des anahtarı tam 8 byte olmalı
    cipher=DES.new(anahtar_8mb, DES.MODE_ECB)
    sifreli_byte = cipher.encrypt(pad(mesaj.encode('utf-8'), 8)) #mesajı 8in katı yap(padding) ve şifrele
    return base64.b64encode(sifreli_byte).decode('utf-8') #byte verisini ağ üzerinden göndermek için metne(base64) çeviriyoruz.

def des_coz(sifreli_metin,anahtar):
    anahtar_8mb = anahtar.ljust(8)[:8].encode('utf-8')
    cipher = DES.new(anahtar_8mb, DES.MODE_ECB)
    sifreli_byte = base64.b64decode(sifreli_metin)
    cozulmus_byte = unpad(cipher.decrypt(sifreli_byte), 8)
    return cozulmus_byte.decode('utf-8')




                   ###########  VERİTABANI HAZIRLIYORUZ ###############
def veritabani_hazirla():
    conn=sqlite3.connect("sistem.db")
    cursor=conn.cursor()

    ### KULLANICILAR TABLOSU ###
    cursor.execute('''CREATE TABLE IF NOT EXISTS kullanicilar (id INTEGER PRIMARY KEY, kullanici_adi TEXT, anahtar TEXT)''')
    ### MESAJLAR TABLOSU ###
    cursor.execute('''CREATE TABLE IF NOT EXISTS mesajlar (id INTEGER PRIMARY KEY, gonderen TEXT, alici TEXT, mesaj TEXT)''')

    conn.commit() #değişiklikleri kaydet
    conn.close() #bağlantıyı güvenli kapat



                   ########### LSB ÇÖZME FONKSİYONU ###############
def resimden_sifre_coz(resim_yolu):
    img=Image.open(resim_yolu)
    pixels=list(img.getdata()) #resimdeki tüm pixelleri bir liste olarak al(r,g,b formatında)
    binary_mesaj=""

    #her pixelin içinde dön
    for pixel in pixels:
        for i in range(3): #her pixelin kırmızı, yeşil, mavi kanalına bak.
            binary_mesaj+=str(pixel[i] & 1) #pixel değerinin son bitini alarak binary_mesaj a ekliyoruz.

    veriler=[binary_mesaj[i:i+8] for i in range(0, len(binary_mesaj), 8)] #toplanan 0 ve 1'leri 8'erli gruplara (byte) böl
    mesaj = ""
    
    for byte in veriler:
            # Eğer byte '11111111' ise şifre bitti demektir, dur!
            if byte == "11111111":
                break
            
            try:
                # Byte'ı karaktere çevir ve mesaja ekle
                karakter = chr(int(byte, 2))
                mesaj += karakter
            except:
                break
                
    return mesaj





                   ########### SUNUCU ANA DÖNGÜSÜ ###############
def sunucuyu_baslat():
    veritabani_hazirla() #veritabaninin hazır olup olmadığını kontrol ediyoruz.
    server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 12345)) #sadece bu bilg.dan gelen bağlantıları kabul eder.Başka bilg. bağl. istersen buraya kendi ip adresini yazarsın.- 12345:port numarasıpt
    server.listen(1) #gelen bağlantıları dinliyor.
    print("Sunucu açıldı, yeni istemciler bekleniyor (Kapatmak için Ctrl+C)..")

    while True: # Bu döngü sayesinde sunucu bir mesaj aldıktan sonra başa döner.
        baglanti,adres=server.accept() #bir istemci bağlandığında kapıyı açar.
        print(f"Bağlantı sağlandı: {adres}")
        
        data=baglanti.recv(1024).decode() #clientden gelen veriyi okur.
        


             ###### KAYIT KISMI #######
        if data.startswith("KAYIT"): #gelen veri kayıt komutuyla başlıyorsa
            k_adi=data.split("|")[1] #kullanıcı adını ayıkla

            # 1. Kullanıcı adı zaten var mı kontrol et
            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi=?", (k_adi,))
            mevcut_kullanici = cursor.fetchone()

            if mevcut_kullanici:
                print(f"HATA: {k_adi} kullanıcı adı zaten alınmış.")
                baglanti.send("HATA|Bu kullanıcı adı zaten kayıtlı!".encode())
                conn.close()
                baglanti.close()
                continue
            else:
                # Kullanıcı yoksa devam et
                baglanti.send("OK".encode()) # İstemciye resim gönderebilirsin onayı veriyoruz
                print(f"Kayıt isteği onaylandı: {k_adi}. Resim bekleniyor...")

            baglanti.settimeout(2.0) # 2 saniye boyunca yeni veri gelmezse resim bitti say

            try:
                with open("gelen_resim.png", "wb") as f:
                    while True:
                        l = baglanti.recv(1024) # 1024'er byte oku
                        if not l: break # Veri bittiyse döngüden çık
                        f.write(l) # Okunan byte'ları dosyaya yaz.
            except socket.timeout:
                pass

            
            try:
                cikarilan_sifre=resimden_sifre_coz("gelen_resim.png") #dosya yazma bittiğinde resim içindeki şifreyi çıkarıyoruz.
                cursor.execute("INSERT INTO kullanicilar (kullanici_adi, anahtar) VALUES (?, ?)", (k_adi, cikarilan_sifre))
                conn.commit()
                conn.close()
                print(f"Kayıt Tamamlandı: {k_adi}")
            except Exception as e:
                print(f"HATA: Resim işlenemedi veya şifre çözülemedi: {e}")





             ####### GİRİŞ KISMI ###########
        elif data.startswith("LOGIN"):
            parcalar = data.split("|")
            k_adi = parcalar[1].strip() # Boşlukları temizle
            girilen_sifre = parcalar[2].strip()
            
            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (k_adi,))
            sonuc = cursor.fetchone()
            
            if sonuc and sonuc[0] == girilen_sifre:
                cursor.execute("SELECT kullanici_adi FROM kullanicilar")
                kullanici_listesi = ",".join([k[0] for k in cursor.fetchall()])
                
                # ÖNEMLİ: Bu sorgu veritabanındaki tüm gidiş-dönüş mesajlarını bulur
                cursor.execute("SELECT gonderen, alici, mesaj FROM mesajlar WHERE alici=? OR gonderen=?", (k_adi, k_adi))
                mesaj_verileri = cursor.fetchall()
                
                gelen_paket = "#".join([f"{m[0]}|{m[1]}|{m[2]}" for m in mesaj_verileri])
                
                # Boş paket gönderilse bile formatın bozulmaması için:
                baglanti.send(f"BASARILI|{kullanici_listesi}|{gelen_paket}".encode())
                print(f"DEBUG: {k_adi} kullanıcısına {len(mesaj_verileri)} mesaj iletildi.")
            else:
                baglanti.send("HATA|Giriş bilgileri yanlış!".encode())
            conn.close()



        ######### MESAJ GÖNDERME / ÇÖZME / ŞİFRELEME #########
      
        elif data.startswith("SEND_MSG"):
            parcalar = data.split("|")
            # Değerleri alırken boşlukları temizle (Çok önemli!)
            gnd = parcalar[1].strip()
            alc = parcalar[2].strip()
            sifreli_mesaj = parcalar[3]

            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            try:
                # 1. Gönderen ve Alıcı anahtarlarını al
                cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (gnd,))
                c1_anahtar = cursor.fetchone()[0]
                cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (alc,))
                c2_anahtar = cursor.fetchone()[0]

                # Orijinal mesajı çıkar (Gönderen anahtarıyla)
                orijinal_mesaj = des_coz(sifreli_mesaj, c1_anahtar)

                # İki kopya kaydet: Biri alıcı için, biri gönderen için (geçmişi görmek adına)
                # Alıcı için şifrele
                msg_alc = des_sifrele(orijinal_mesaj, c2_anahtar)
                cursor.execute("INSERT INTO mesajlar (gonderen, alici, mesaj) VALUES (?, ?, ?)", (gnd, alc, msg_alc))
                
                # Gönderen için şifrele
                msg_gnd = des_sifrele(orijinal_mesaj, c1_anahtar)
                cursor.execute("INSERT INTO mesajlar (gonderen, alici, mesaj) VALUES (?, ?, ?)", (gnd, alc, msg_gnd))

                conn.commit()
                print(f"DEBUG: {gnd} -> {alc} mesajı DB'ye çift taraflı kaydedildi.")
            except Exception as e:
                print(f"DEBUG: Mesaj kaydetme hatası: {e}")
            finally:
                conn.close()

        

<<<<<<< Updated upstream
        baglanti.close() #Sadece o anki bağlantıyı kapatır, sunucu (server) açık kalır.
=======
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
>>>>>>> Stashed changes

#Eğer bu dosya doğrudan çalıştırılıyorsa sunucuyu başlat
if __name__ == "__main__":
    sunucuyu_baslat()