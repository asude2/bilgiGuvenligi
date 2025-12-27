import socket
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image
import os
import time
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad

# ########## DES FONKSİYONLARI ##########
def des_sifrele(mesaj, anahtar):
    anahtar_8 = anahtar.ljust(8)[:8].encode('utf-8')
    cipher = DES.new(anahtar_8, DES.MODE_ECB)
    return cipher.encrypt(pad(mesaj.encode('utf-8'), 8))

def des_coz(sifreli_byte, anahtar):
    anahtar_8 = anahtar.ljust(8)[:8].encode('utf-8')
    cipher = DES.new(anahtar_8, DES.MODE_ECB)
    return unpad(cipher.decrypt(sifreli_byte), 8).decode('utf-8')

# ########## LSB GİZLEME ##########
def lsb_gizle(resim_yolu, sifre, cikis_adi="gonderilecek.png"):
    img = Image.open(resim_yolu).convert('RGB')
    veriler = list(img.getdata())
    binary_mesaj = ''.join(format(ord(i), '08b') for i in sifre) + '1111111111111111'
    yeni_veriler = []
    mesaj_index = 0
    for pixel in veriler:
        yeni_pixel = list(pixel)
        for i in range(3):
            if mesaj_index < len(binary_mesaj):
                yeni_pixel[i] = (yeni_pixel[i] & ~1) | int(binary_mesaj[mesaj_index])
                mesaj_index += 1
        yeni_veriler.append(tuple(yeni_pixel))
    yeni_img = Image.new(img.mode, img.size)
    yeni_img.putdata(yeni_veriler)
    yeni_img.save(cikis_adi, "PNG")
    return cikis_adi

# ########## MESAJLAŞMA EKRANI ##########
def mesajlasma_ekranini_ac(kullanici_adi, anahtar, kullanici_listesi):
    # Toplevel yerine tk.Toplevel yazarak hatayı önledik
    msg_pencere = tk.Toplevel(root)
    msg_pencere.title(f"Sohbet: {kullanici_adi}")
    msg_pencere.geometry("400x550")

    tk.Label(msg_pencere, text="Aktif Kullanıcılar:").pack(pady=5)
    lb_kullanicilar = tk.Listbox(msg_pencere)
    for k in kullanici_listesi.split(','):
        if k and k != kullanici_adi: 
            lb_kullanicilar.insert(tk.END, k)
    lb_kullanicilar.pack(fill=tk.BOTH, expand=True, padx=10)

    tk.Label(msg_pencere, text="Mesajınız:").pack(pady=5)
    txt_mesaj = tk.Entry(msg_pencere)
    txt_mesaj.pack(fill=tk.X, padx=10)

    def mesaj_gonder():
        secili = lb_kullanicilar.get(tk.ACTIVE)
        mesaj_metni = txt_mesaj.get()
        if not secili or not mesaj_metni:
            messagebox.showwarning("Uyarı", "Alıcı seçin ve mesaj yazın!")
            return
        
        sifreli_mesaj = des_sifrele(mesaj_metni, anahtar)
        try:
            istemci = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            istemci.connect(('localhost', 12345))
            baslik = f"MESAJ_AT|{kullanici_adi}|{secili}|".encode()
            istemci.send(baslik + sifreli_mesaj)
            messagebox.showinfo("Başarılı", "Mesaj DES ile şifrelendi!")
            txt_mesaj.delete(0, tk.END)
            istemci.close()
        except Exception as e:
            messagebox.showerror("Hata", f"Gönderilemedi: {e}")

    tk.Button(msg_pencere, text="DES ŞİFRELİ GÖNDER", command=mesaj_gonder, bg="green", fg="white").pack(pady=10)

# ########## GİRİŞ YAP ##########
def giris_yap():
    k_adi = entry_kullanici.get()
    sifre = entry_sifre.get()
    try:
        istemci = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        istemci.connect(('localhost', 12345))
        istemci.send(f"LOGIN|{k_adi}|{sifre}".encode())
        cevap = istemci.recv(4096).decode()
        if cevap.startswith("BASARILI"):
            k_liste = cevap.split("|")[1]
            root.withdraw()
            mesajlasma_ekranini_ac(k_adi, sifre, k_liste)
        else:
            messagebox.showerror("Hata", "Giriş başarısız!")
        istemci.close()
    except Exception as e:
        messagebox.showerror("Hata", f"Bağlantı hatası: {e}")

# ########## KAYIT OL ##########
def kayit_ol():
    k_adi, sifre, yol = entry_kullanici.get(), entry_sifre.get(), label_resim_yolu.cget("text")
    if not k_adi or not sifre or "Seçilmedi" in yol:
        messagebox.showwarning("Hata", "Eksik bilgi!")
        return
    try:
        hazir_resim = lsb_gizle(yol, sifre)
        istemci = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        istemci.connect(('localhost', 12345))
        istemci.send(f"KAYIT|{k_adi}".encode())
        if istemci.recv(1024).decode() == "OK":
            time.sleep(0.2)
            with open(hazir_resim, "rb") as f:
                istemci.sendall(f.read())
            messagebox.showinfo("Başarılı", "Kayıt tamam!")
        istemci.close()
    except Exception as e:
        messagebox.showerror("Hata", f"Hata: {e}")

def resim_sec():
    yol = filedialog.askopenfilename(filetypes=[("Resim Dosyaları", "*.png *.jpg *.jpeg")])
    if yol:
        label_resim_yolu.config(text=yol)

# ########## ANA ARAYÜZ ##########
root = tk.Tk()
root.title("Kayıt/Giriş")
root.geometry("400x400")

tk.Label(root, text="Kullanıcı Adı:").pack(pady=5)
entry_kullanici = tk.Entry(root)
entry_kullanici.pack()

tk.Label(root, text="Şifre (DES Anahtarı):").pack(pady=5)
entry_sifre = tk.Entry(root, show="*")
entry_sifre.pack()

tk.Button(root, text="Resim Seç", command=resim_sec).pack(pady=10)
label_resim_yolu = tk.Label(root, text="Resim Seçilmedi", fg="blue", font=("Arial", 8))
label_resim_yolu.pack()

tk.Button(root, text="GİRİŞ YAP", command=giris_yap, bg="blue", fg="white", width=20).pack(pady=5)
tk.Button(root, text="KAYIT OL (LSB)", command=kayit_ol, bg="green", fg="white", width=20).pack()

root.mainloop()