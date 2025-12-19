import socket  #pythonun ağ iletişimi için kullandığı kütüph.
import sqlite3
import os #dosya işl. yönetmek için
from PIL import Image #resmi LSB ile çözmek için



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
            parcalar=data.split("|")

            if len(parcalar) < 3:
                baglanti.send("HATA|Eksik bilgi gönderildi!".encode())
                baglanti.close()
                continue

            k_adi = parcalar[1]
            girilen_sifre = parcalar[2]
            print(f"Giriş isteği geldi: {k_adi}. Şifre kontrol ediliyor...")
            
            #2.Veritabanından bu kullanıcının gerçek şifresini çek
            conn = sqlite3.connect("sistem.db")
            cursor = conn.cursor()
            cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (k_adi,))
            sonuc = cursor.fetchone()
            
            if sonuc and sonuc[0] == girilen_sifre:
                #3. Giriş başarılıysa tüm kullanıcıları al
                cursor.execute("SELECT kullanici_adi FROM kullanicilar")
                kullanicilar = cursor.fetchall() 
                
                kullanici_listesi = ",".join([k[0] for k in kullanicilar])
                
                baglanti.send(f"BASARILI|{kullanici_listesi}".encode())
                print(f"Giriş Başarılı: {k_adi}")
            else:
                baglanti.send("HATA|Kullanıcı adı veya şifre yanlış!".encode())
                print(f"Giriş Başarısız: {k_adi}")
            
            conn.close()

        baglanti.close() #Sadece o anki bağlantıyı kapatır, sunucu (server) açık kalır.

#Eğer bu dosya doğrudan çalıştırılıyorsa sunucuyu başlat
if __name__ == "__main__":
    sunucuyu_baslat()