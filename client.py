import socket        
from tkinter import *
from tkinter import filedialog, messagebox #dosya seçme penceresi ve uyarı mesajları için
from PIL import Image  
import os       
import time  #sunucuyla veri alışverişinde kısa beklemeler eklemek için      

            ########## LSB GİZLEME FONKSİYONU ############
def lsb_gizle(resim_yolu, sifre, cikis_adi="gonderilecek.png"):
    img = Image.open(resim_yolu) 
    img = img.convert('RGB')   #resmin renk formatını standart RGB yap
    veriler = list(img.getdata()) #resmin tüm piksellerini sayısal listeye çevir
    
    binary_mesaj = ''.join(format(ord(i), '08b') for i in sifre) + '1111111111111111'

    yeni_veriler = []
    mesaj_index = 0
    
    for pixel in veriler:
        yeni_pixel = list(pixel) #pikseli (R,G,B) listesine çeviriyoruz ki değiştirebilelim
        for i in range(3): # R, G ve B kanallarının her birine bak
            if mesaj_index < len(binary_mesaj):
                # LSB: Sayının son bitini sil (& ~1) ve mesajın bitini ekle (| int)
                yeni_pixel[i] = (yeni_pixel[i] & ~1) | int(binary_mesaj[mesaj_index])
                mesaj_index += 1
        yeni_veriler.append(tuple(yeni_pixel)) # Değişen pikseli yeni listeye ekle
    
    yeni_img = Image.new(img.mode, img.size) # Aynı boyutlarda yeni bir resim oluştur
    yeni_img.putdata(yeni_veriler)           # Hazırlanan pikselleri resme yerleştir
    yeni_img.save(cikis_adi, "PNG")          # Veri kaybı olmaması için PNG olarak kaydet
    return cikis_adi




               ########### SUNUCUYA GÖNDERME FONKSİYONU #############
def kayit_ol():   #arayüzdeki değerleri alıyoruz.
    k_adi = entry_kullanici.get() 
    sifre = entry_sifre.get()  
    resim_yolu = label_resim_yolu.cget("text")
    
    if not k_adi or not sifre or "Seçilmedi" in resim_yolu:
        messagebox.showwarning("Hata", "Lütfen tüm alanları doldurun ve resim seçin!")
        return

    try:
        #1. Şifreyi resme gizle
        hazir_resim = lsb_gizle(resim_yolu, sifre)
        #2. Sunucuya bağlan
        istemci = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        istemci.connect(('localhost', 12345))
        #3. Önce komutu gönder (KAYIT|kullanici_adi)
        komut = f"KAYIT|{k_adi}"
        istemci.send(komut.encode())

        cevap = istemci.recv(1024).decode()
        if cevap.startswith("HATA"):
            messagebox.showerror("Hata", cevap.split("|")[1])
            istemci.close()
            return # Fonksiyondan çık, resmi gönderme!

        #sunucunun komutu işlemesi için çok kısa bekle
        time.sleep(0.2)
        #4. Hazırlanan şifreli resmi byte byte gönder
        with open(hazir_resim, "rb") as f:
            while True:
                byte_verisi = f.read(1024)
                if not byte_verisi: break
                istemci.send(byte_verisi)
        
        messagebox.showinfo("Başarılı", "Kayıt başarıyla tamamlandı!")
        istemci.close()
    except Exception as e:
        messagebox.showerror("Hata", f"Bağlantı hatası: {e}")


def giris_yap():
    k_adi = entry_kullanici.get()
    sifre = entry_sifre.get()
    
    if not k_adi or not sifre:
        messagebox.showwarning("Hata", "Lütfen tüm alanları doldurun!")
        return

    try:
        istemci = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        istemci.connect(('localhost', 12345))
        veri=f"LOGIN|{k_adi}|{sifre}"
        istemci.send(veri.encode())
        cevap = istemci.recv(4096).decode() #sunucudan cevap bekliyoruz.

        if cevap.startswith("BASARILI"):
            parcalar = cevap.split("|")
            liste = parcalar[1] if len(parcalar) > 1 else ""
            temiz_liste = liste.replace(',', '\n')
            messagebox.showinfo("Giriş Başarılı", f"Sistemdeki Kullanıcılar:\n{temiz_liste}")
        else:
            hata_mesaji = cevap.split("|")[1] if "|" in cevap else "Bilinmeyen hata"
            messagebox.showerror("Hata", hata_mesaji)
            
            
        istemci.close()
    except Exception as e:
        messagebox.showerror("Hata", f"Giriş sırasında hata: {e}")



       ############# RESİM SEÇME PENCERESİ ################
def resim_sec():
    yol = filedialog.askopenfilename(filetypes=[("Resim Dosyaları", "*.png *.jpg *.jpeg")])
    if yol:
        label_resim_yolu.config(text=yol)

        ############ ARAYÜZ TASARIMI ############
root = Tk()
root.title("Kayıt Ol / Giriş Yap")
root.geometry("400x300")

Label(root, text="Kullanıcı Adı:").pack(pady=5)
entry_kullanici = Entry(root)
entry_kullanici.pack()

Label(root, text="Şifre (Resme Gizlenecek):").pack(pady=5)
entry_sifre = Entry(root, show="*") #şifreyi yıldızlı gösteriyor.
entry_sifre.pack()

# Resim seçme alanı (Sadece kayıt için olduğunu belirten bir etiket ekledik)
Label(root, text="--- Kayıt İşlemi İçin Resim Gerekli ---", fg="gray").pack(pady=5)
Button(root, text="Kayıt İçin Resim Seç", command=resim_sec).pack()
label_resim_yolu = Label(root, text="Resim Seçilmedi", fg="blue", font=("Arial", 8))
label_resim_yolu.pack()

# Butonlar
Button(root, text="GİRİŞ YAP", command=giris_yap, bg="blue", fg="white", width=20).pack(pady=10)
Button(root, text="KAYIT OL", command=kayit_ol, bg="green", fg="white", width=20).pack()


root.mainloop()


