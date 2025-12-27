import socket        
from tkinter import *
from tkinter import filedialog, messagebox #dosya seçme penceresi ve uyarı mesajları için
from PIL import Image  
import os       
import time  #sunucuyla veri alışverişinde kısa beklemeler eklemek için    
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





########## MESAJLAŞMA KISMI KULLANICI LİSTESİ VE MESAJ YAZMA YERİ ARAYÜZÜ #############

def mesajlasma_penceresini_ac(kullanici_adi, aktif_kullanicilar, kendi_sifren, gelen_mesajlar_paketi):
    root.withdraw()
    mesaj_penceresi = Toplevel()
    mesaj_penceresi.title(f"Mesajlaşma Paneli - {kullanici_adi}")
    mesaj_penceresi.geometry("600x450")

    #sunucudan gelen tüm mesajları bir liste nesnesine dönüştürelim
    tum_mesajlar = []
    if gelen_mesajlar_paketi and len(gelen_mesajlar_paketi.strip()) > 0:
        print(f"Sunucudan Gelen Ham Veri: {gelen_mesajlar_paketi}")
        parcalar = gelen_mesajlar_paketi.split("#")
        for p in parcalar:
            detay = p.split("|")
            if len(detay) == 3:
                tum_mesajlar.append({"gnd": detay[0], "alc": detay[1], "msg": detay[2]})
    else:
        print("Görüntülenecek mesaj bulunamadı.")

    # --- SOL TARAF: KULLANICI LİSTESİ ---
    frame_sol = Frame(mesaj_penceresi)
    frame_sol.pack(side=LEFT, fill=Y, padx=10, pady=10)
    Label(frame_sol, text="Kullanıcılar", font=("Arial", 10, "bold")).pack()
    lb_kullanicilar = Listbox(frame_sol, width=20, height=20)
    lb_kullanicilar.pack(pady=5)
    
    for user in aktif_kullanicilar.split("\n"):
        if user and user != kullanici_adi: 
            lb_kullanicilar.insert(END, user)

    # --- SAĞ TARAF: MESAJLAŞMA ALANI ---
    frame_sag = Frame(mesaj_penceresi)
    frame_sag.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)
    lbl_sohbet_baslik = Label(frame_sag, text="Lütfen bir kullanıcı seçin", font=("Arial", 10, "bold"))
    lbl_sohbet_baslik.pack()
    
    mesaj_alani = Text(frame_sag, width=40, height=15, state=DISABLED, bg="#f0f0f0")
    mesaj_alani.pack(pady=5, fill=BOTH, expand=True)
    mesaj_alani.tag_config("giden", foreground="green")
    mesaj_alani.tag_config("gelen", foreground="blue")

    # --- FİLTRELEME FONKSİYONU ---
    def sohbeti_yukle(event):
        secili_index = lb_kullanicilar.curselection()
        if not secili_index: return
        
        hedef_kisi = lb_kullanicilar.get(secili_index)
        lbl_sohbet_baslik.config(text=f"{hedef_kisi} ile Sohbet")
        
        mesaj_alani.config(state=NORMAL)
        mesaj_alani.delete('1.0', END) # Önceki yazıları temizle
        
        for m in tum_mesajlar:
            if (m["gnd"] == hedef_kisi and m["alc"] == kullanici_adi) or \
               (m["gnd"] == kullanici_adi and m["alc"] == hedef_kisi):
                
                mesaj_alani.config(state=NORMAL)
                try:
                    # Kendi anahtarımızla çözmeye çalış
                    cozulmus = des_coz(m["msg"], kendi_sifren)
                    if m["alc"] == kullanici_adi:
                        mesaj_alani.insert(END, f"[{m['gnd']}]: {cozulmus}\n", "gelen")
                    else:
                        mesaj_alani.insert(END, f"[Sen]: {cozulmus}\n", "giden")
                except Exception as e:
                    # Çözemezse hatayı ve şifreli hali yazdır (Hata ayıklama için)
                    mesaj_alani.insert(END, f"[{m['gnd']}]: [Kilitli Mesaj: {m['msg'][:10]}...]\n")
                    print(f"Deşifre Hatası: {e}")
                mesaj_alani.config(state=DISABLED)
                  
        mesaj_alani.see(END)

    # Listbox'a tıklama olayını bağla
    lb_kullanicilar.bind('<<ListboxSelect>>', sohbeti_yukle)

    # --- MESAJ GÖNDERME KISMI ---
    frame_alt = Frame(frame_sag)
    frame_alt.pack(fill=X, pady=5)
    mesaj_giris = Entry(frame_alt)
    mesaj_giris.pack(side=LEFT, fill=X, expand=True)

    def mesaj_gonder_butonu():
        secili_index = lb_kullanicilar.curselection()
        if not secili_index:
            messagebox.showwarning("Hata", "Lütfen bir alıcı seçin!")
            return
        
        hedef_kisi = lb_kullanicilar.get(secili_index)
        mesaj = mesaj_giris.get()
        if not mesaj: return

        try:
            sifreli_mesaj = des_sifrele(mesaj, kendi_sifren)
            istemci = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            istemci.connect(('localhost', 12345))
            paket = f"SEND_MSG|{kullanici_adi}|{hedef_kisi}|{sifreli_mesaj}"
            istemci.send(paket.encode())
            istemci.close()
            
            # Kendi ekranımızı hemen güncellemek için listeye ekle
            tum_mesajlar.append({"gnd": kullanici_adi, "alc": hedef_kisi, "msg": sifreli_mesaj})
            sohbeti_yukle(None) # Ekranı tazele
            mesaj_giris.delete(0, END)
        except Exception as e:
            messagebox.showerror("Hata", f"Hata: {e}")

    Button(frame_alt, text="Gönder", command=mesaj_gonder_butonu, bg="green", fg="white").pack(side=RIGHT, padx=5)
    mesaj_penceresi.protocol("WM_DELETE_WINDOW", lambda: root.destroy())
    







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
            temiz_liste = parcalar[1].replace(',', '\n')
            gelen_mesajlar_paketi = parcalar[2] if len(parcalar) > 2 else ""
            mesajlasma_penceresini_ac(k_adi, temiz_liste, sifre, gelen_mesajlar_paketi) #pencereyi açarken mesaj paketini de gönderiyoruz.
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
