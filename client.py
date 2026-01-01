import socket
from tkinter import *
from tkinter import filedialog, messagebox
from PIL import Image
import time
import threading
from Crypto.Cipher import DES
import binascii


# --- ŞİFRELEME (DES) ---
def pad(text):
    while len(text) % 8 != 0: text += ' '
    return text


def des_sifrele(mesaj, anahtar):
    try:
        des = DES.new(anahtar.encode(), DES.MODE_ECB)
        sifreli = des.encrypt(pad(mesaj).encode())
        return binascii.hexlify(sifreli).decode()
    except:
        return ""


def des_coz(sifreli_hex, anahtar):
    try:
        des = DES.new(anahtar.encode(), DES.MODE_ECB)
        cozulmus = des.decrypt(binascii.unhexlify(sifreli_hex))
        return cozulmus.decode().strip()
    except:
        return "[Sifreli Veri Cozulemedi]"


# --- LSB GİZLEME ---
def lsb_gizle(resim_yolu, sifre, cikis_adi="gonderilecek.png"):
    img = Image.open(resim_yolu)
    img = img.convert('RGB')
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


# --- Global Değişkenler ---
istemci_socket = None
aktif_kullanici_adi = ""
aktif_sifre_anahtari = ""

# HAFIZA: {"Ahmet": "Sen: Selam\nAhmet: A.selam\n", "Mehmet": "..."}
sohbet_gecmisi = {}
su_an_konusulan_kisi = None


def anahtari_duzenle(sifre):
    if len(sifre) > 8: return sifre[:8]
    while len(sifre) < 8: sifre += "0"
    return sifre


def kayit_ol():
    k_adi = entry_kullanici.get()
    sifre = entry_sifre.get()
    resim_yolu = label_resim_yolu.cget("text")

    if not k_adi or not sifre or "Secilmedi" in resim_yolu:
        messagebox.showwarning("Hata", "Alanlari doldurun!")
        return

    try:
        hazir_resim = lsb_gizle(resim_yolu, sifre)
        tmp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tmp_sock.connect(('localhost', 12345))

        tmp_sock.send(f"KAYIT|{k_adi}".encode())
        cevap = tmp_sock.recv(1024).decode()

        if cevap == "OK":
            time.sleep(0.2)
            with open(hazir_resim, "rb") as f:
                while True:
                    data = f.read(2048)
                    if not data: break
                    tmp_sock.send(data)

            try:
                son_cevap = tmp_sock.recv(1024).decode()
                if "KAYIT_BASARILI" in son_cevap:
                    messagebox.showinfo("Basarili", "Kayit tamamlandi! Giris yapin.")
                else:
                    messagebox.showerror("Hata", f"Sunucu: {son_cevap}")
            except:
                pass
        else:
            messagebox.showerror("Hata", cevap)

        tmp_sock.close()
    except Exception as e:
        messagebox.showerror("Hata", str(e))


def giris_yap():
    global istemci_socket, aktif_kullanici_adi, aktif_sifre_anahtari
    k_adi = entry_kullanici.get()
    sifre = entry_sifre.get()

    try:
        istemci_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        istemci_socket.connect(('localhost', 12345))

        istemci_socket.send(f"LOGIN|{k_adi}|{sifre}".encode())
        cevap = istemci_socket.recv(8192).decode()

        if cevap.startswith("BASARILI"):
            aktif_kullanici_adi = k_adi
            aktif_sifre_anahtari = anahtari_duzenle(sifre)
            parcalar = cevap.split("|")
            offline_msg = parcalar[1]
            users_list_str = "|".join(parcalar[2:])
            pencere_chat_ac(offline_msg, users_list_str)
        else:
            messagebox.showerror("Hata", cevap)
            istemci_socket.close()

    except Exception as e:
        messagebox.showerror("Hata", str(e))


# --- Chat Ekranı (GUI) ---
def pencere_chat_ac(offline_mesajlar, users_raw):
    global su_an_konusulan_kisi

    root.withdraw()
    chat_win = Toplevel(root)
    chat_win.title(f"Chat - {aktif_kullanici_adi}")
    chat_win.geometry("750x500")

    # SOL TARAFTAKİ LİSTE
    left_frame = Frame(chat_win, width=220, bg="#e5e5e5")
    left_frame.pack(side=LEFT, fill=Y)

    Label(left_frame, text="KISILER", bg="#075e54", fg="white", font=("Arial", 12, "bold"), pady=10).pack(fill=X)

    user_listbox = Listbox(left_frame, width=30, height=25, bg="white", selectmode=SINGLE, font=("Arial", 10))
    user_listbox.pack(padx=5, pady=5)

    label_info = Label(chat_win, text="<- Sohbet icin kisi secin", fg="gray")
    label_info.pack(pady=10)

    def listeyi_guncelle(raw_data=None):
        mevcut_secim_index = user_listbox.curselection()
        user_listbox.delete(0, END)
        if not raw_data: return

        parts = raw_data.split("|")
        online_part = parts[0].split(":")[1] if len(parts) > 0 else ""
        offline_part = parts[1].split(":")[1] if len(parts) > 1 else ""

        onlines = [u for u in online_part.split(",") if u]
        offlines = [u for u in offline_part.split(",") if u]

        for u in onlines:
            if u != aktif_kullanici_adi:
                user_listbox.insert(END, f"[ON] {u}")
                user_listbox.itemconfig(END, {'fg': 'green'})

        for u in offlines:
            if u != aktif_kullanici_adi:
                user_listbox.insert(END, f"[OFF] {u}")
                user_listbox.itemconfig(END, {'fg': 'gray'})

    listeyi_guncelle(users_raw)

    def sunucudan_liste_iste():
        istemci_socket.send("LISTE_GUNCELLE".encode())

    Button(left_frame, text="YENILE", command=sunucudan_liste_iste, bg="#25D366", fg="white").pack(pady=5, fill=X)

    # SAĞ TARAFTAKİ MESAJLAŞMA
    right_frame = Frame(chat_win, bg="#ece5dd")
    right_frame.pack(side=RIGHT, expand=True, fill=BOTH)

    text_area = Text(right_frame, height=20, state='disabled', bg="#ece5dd", font=("Arial", 11))
    text_area.pack(expand=True, fill=BOTH, padx=10, pady=10)

    entry_mesaj = Entry(right_frame, font=("Arial", 12))
    entry_mesaj.pack(fill=X, padx=10, pady=5)

    def sohbeti_ekrana_yukle(kisi_adi):
        text_area.config(state='normal')
        text_area.delete('1.0', END)
        if kisi_adi in sohbet_gecmisi:
            text_area.insert(END, sohbet_gecmisi[kisi_adi])
        text_area.config(state='disabled')
        text_area.see(END)
        label_info.config(text=f"Sohbet: {kisi_adi}", fg="green", font=("Arial", 10, "bold"))

    def kisi_sec(event):
        global su_an_konusulan_kisi
        secim = user_listbox.get(ANCHOR)
        if secim:
            isim = secim.replace("[ON] ", "").replace("[OFF] ", "").strip()
            su_an_konusulan_kisi = isim
            sohbeti_ekrana_yukle(isim)

    user_listbox.bind('<Double-Button-1>', kisi_sec)

    # OFFLINE MESAJLARI HAFIZAYA YUKLE
    def ekrana_ve_hafizaya_yaz(kisi, mesaj_satiri):
        if kisi not in sohbet_gecmisi: sohbet_gecmisi[kisi] = ""
        sohbet_gecmisi[kisi] += mesaj_satiri + "\n"

        if su_an_konusulan_kisi == kisi:
            text_area.config(state='normal')
            text_area.insert(END, mesaj_satiri + "\n")
            text_area.config(state='disabled')
            text_area.see(END)

    if offline_mesajlar and offline_mesajlar != "YOK":
        msgs = offline_mesajlar.split("###")
        for m in msgs:
            gonderen, icerik = m.split(":", 1)
            ekrana_ve_hafizaya_yaz(gonderen, f"{gonderen}: {icerik}")
        messagebox.showinfo("Bilgi", "Okunmamis mesajlariniz yuklendi.")

    # MESAJ GÖNDERME
    def gonder(event=None):
        if not su_an_konusulan_kisi:
            messagebox.showwarning("Hata", "Lutfen bir kisi secin!")
            return

        mesaj = entry_mesaj.get()
        if not mesaj: return

        # 1. Şifrele
        sifreli_mesaj = des_sifrele(mesaj, aktif_sifre_anahtari)

        # 2. Sunucuya Gönder
        komut = f"MSG|{su_an_konusulan_kisi}|{sifreli_mesaj}"
        istemci_socket.send(komut.encode())

        # 3. Kendi ekranına yaz
        ekrana_ve_hafizaya_yaz(su_an_konusulan_kisi, f"Sen: {mesaj}")
        entry_mesaj.delete(0, END)

    entry_mesaj.bind("<Return>", gonder)
    Button(right_frame, text="GONDER", command=gonder, bg="#128C7E", fg="white", font=("Arial", 10, "bold")).pack(
        pady=5)

    # DİNLEME THREAD'İ
    def gelenleri_dinle():
        while True:
            try:
                veri = istemci_socket.recv(4096).decode()
                if not veri: break

                if veri.startswith("GELEN"):
                    _, kimden, sifreli_msj = veri.split("|", 2)

                    # GELEN ŞİFRELİ MESAJI ÇÖZ (Rubric: Alıcı Deşifreleyebilme)
                    cozulmus_msj = des_coz(sifreli_msj, aktif_sifre_anahtari)

                    ekrana_ve_hafizaya_yaz(kimden, f"{kimden}: {cozulmus_msj}")

                elif veri.startswith("LISTE"):
                    _, liste_verisi = veri.split("|", 1)
                    # Listeyi güncellerken seçimi korumak zor olduğu için basitçe yeniliyoruz
                    user_listbox.delete(0, END)
                    listeyi_guncelle(liste_verisi)
            except:
                break

    threading.Thread(target=gelenleri_dinle, daemon=True).start()


def resim_sec():
    yol = filedialog.askopenfilename(filetypes=[("Resim", "*.png *.jpg")])
    if yol: label_resim_yolu.config(text=yol)


# --- Arayüz ---
root = Tk()
root.title("Giris Paneli")
root.geometry("300x350")

Label(root, text="Kullanici Adi:").pack(pady=5)
entry_kullanici = Entry(root)
entry_kullanici.pack()

Label(root, text="Sifre:").pack(pady=5)
entry_sifre = Entry(root, show="*")
entry_sifre.pack()

Label(root, text="--- Kayit Icin ---", fg="gray").pack(pady=10)
Button(root, text="Resim Sec", command=resim_sec).pack()
label_resim_yolu = Label(root, text="Secilmedi", fg="blue")
label_resim_yolu.pack()

Button(root, text="GIRIS YAP", command=giris_yap, bg="lightblue", width=20, height=2).pack(pady=10)
Button(root, text="KAYIT OL", command=kayit_ol, bg="lightgreen", width=20).pack()

root.mainloop()