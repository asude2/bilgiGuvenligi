import socket
import sqlite3
import threading
from PIL import Image
from Crypto.Cipher import DES
import binascii
import os


# --- Veritabanı ---
def veritabani_hazirla():
    conn = sqlite3.connect("sistem.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS kullanicilar (kullanici_adi TEXT PRIMARY KEY, anahtar TEXT)')
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS mesajlar (gonderen TEXT, alici TEXT, mesaj TEXT, tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()


# --- Şifreleme Araçları ---
def anahtari_duzenle(sifre):
    # Anahtar tam 8 byte olmalı
    if len(sifre) > 8: return sifre[:8]
    while len(sifre) < 8: sifre += "0"
    return sifre


def pad(text):
    # Metni 8'in katlarına tamamla
    while len(text) % 8 != 0: text += ' '
    return text


def des_coz(sifreli_hex, anahtar):
    try:
        des = DES.new(anahtar.encode(), DES.MODE_ECB)
        cozulmus = des.decrypt(binascii.unhexlify(sifreli_hex))
        return cozulmus.decode().strip()
    except:
        return "COZULEMEDI"


def des_sifrele(mesaj, anahtar):
    try:
        des = DES.new(anahtar.encode(), DES.MODE_ECB)
        sifreli = des.encrypt(pad(mesaj).encode())
        return binascii.hexlify(sifreli).decode()
    except:
        return ""


def resimden_sifre_coz(resim_yolu):
    try:
        img = Image.open(resim_yolu)
        pixels = list(img.getdata())
        binary_mesaj = ""
        # Performans için ilk 4000 piksel yeterli
        limit = 4000 if len(pixels) > 4000 else len(pixels)

        for i in range(limit):
            pixel = pixels[i]
            for j in range(3):
                binary_mesaj += str(pixel[j] & 1)

        veriler = [binary_mesaj[i:i + 8] for i in range(0, len(binary_mesaj), 8)]
        mesaj = ""
        for byte in veriler:
            if byte == "11111111": break
            try:
                mesaj += chr(int(byte, 2))
            except:
                break
        return mesaj
    except Exception as e:
        print(f"Resim hatası: {e}")
        return "HATA"


# --- Sunucu Mantığı ---
aktif_istemciler = {}


def kullanici_listesini_getir():
    try:
        conn = sqlite3.connect("sistem.db")
        cursor = conn.cursor()
        cursor.execute("SELECT kullanici_adi FROM kullanicilar")
        tum_kullanicilar = [row[0] for row in cursor.fetchall()]
        conn.close()

        online_list = []
        offline_list = []
        for k in tum_kullanicilar:
            if k in aktif_istemciler:
                online_list.append(k)
            else:
                offline_list.append(k)
        return f"ONLINE:{','.join(online_list)}|OFFLINE:{','.join(offline_list)}"
    except:
        return "ONLINE:|OFFLINE:"


def istemciyi_dinle(client_socket, adres):
    kullanici_adi = ""
    print(f"[BAGLANTI] {adres} geldi.")
    try:
        while True:
            try:
                data = client_socket.recv(4096).decode()
            except:
                break

            if not data: break

            # --- KAYIT ---
            if data.startswith("KAYIT"):
                try:
                    _, k_adi = data.split("|")
                    client_socket.send("OK".encode())

                    dosya_adi = f"{k_adi}_key.png"
                    with open(dosya_adi, "wb") as f:
                        client_socket.settimeout(3.0)
                        try:
                            while True:
                                img_data = client_socket.recv(4096)
                                if not img_data: break
                                f.write(img_data)
                        except socket.timeout:
                            pass

                    client_socket.settimeout(None)
                    anahtar = resimden_sifre_coz(dosya_adi)

                    conn = sqlite3.connect("sistem.db")
                    try:
                        conn.execute("INSERT INTO kullanicilar VALUES (?, ?)", (k_adi, anahtar))
                        conn.commit()
                        print(f"[KAYIT] {k_adi} eklendi. Anahtarı: {anahtar}")
                        client_socket.send("KAYIT_BASARILI".encode())
                    except sqlite3.IntegrityError:
                        client_socket.send("HATA|Kullanici adi dolu".encode())
                    conn.close()
                    break
                except Exception as e:
                    print(f"Kayıt Hatası: {e}")
                    break

            # --- LOGIN ---
            elif data.startswith("LOGIN"):
                parts = data.split("|")
                k_adi = parts[1]
                girilen_sifre = parts[2]

                conn = sqlite3.connect("sistem.db")
                cursor = conn.cursor()
                cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (k_adi,))
                row = cursor.fetchone()

                if row and row[0] == girilen_sifre:
                    kullanici_adi = k_adi
                    aktif_istemciler[k_adi] = client_socket

                    # Offline Mesajları Çek ve Sil
                    cursor.execute("SELECT gonderen, mesaj FROM mesajlar WHERE alici=?", (k_adi,))
                    mesajlar = cursor.fetchall()
                    msg_str = "YOK"
                    if mesajlar:
                        msg_str = "###".join([f"{m[0]}:{m[1]}" for m in mesajlar])
                        cursor.execute("DELETE FROM mesajlar WHERE alici=?", (k_adi,))
                        conn.commit()

                    users_str = kullanici_listesini_getir()
                    client_socket.send(f"BASARILI|{msg_str}|{users_str}".encode())
                    print(f"[LOGIN] {k_adi} girdi.")
                else:
                    client_socket.send("HATA|Hatali Giris".encode())
                conn.close()

            # --- LİSTE GÜNCELLEME ---
            elif data == "LISTE_GUNCELLE":
                users_str = kullanici_listesini_getir()
                client_socket.send(f"LISTE|{users_str}".encode())

            # --- MESAJLAŞMA (DES ŞİFRELEMELİ) ---
            elif data.startswith("MSG"):
                # Gelen Format: MSG|Alici|SIFRELI_HEX
                _, alici, sifreli_mesaj = data.split("|")

                conn = sqlite3.connect("sistem.db")
                cursor = conn.cursor()

                # 1. Gönderenin anahtarını bul ve mesajı ÇÖZ
                cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (kullanici_adi,))
                res = cursor.fetchone()

                if res:
                    gonderen_anahtar = anahtari_duzenle(res[0])
                    # İstemciden gelen şifreli mesajı çözüyoruz (Rubric #10)
                    cozulmus_mesaj = des_coz(sifreli_hex=sifreli_mesaj, anahtar=gonderen_anahtar)
                    print(f"[MESAJ] {kullanici_adi} -> {alici}: {cozulmus_mesaj} (Şifreli geldi, çözüldü)")

                    if alici in aktif_istemciler:
                        # ALICI ONLINE İSE:
                        try:
                            # 2. Alıcının anahtarını bul
                            cursor.execute("SELECT anahtar FROM kullanicilar WHERE kullanici_adi=?", (alici,))
                            alici_res = cursor.fetchone()
                            if alici_res:
                                alici_anahtari = anahtari_duzenle(alici_res[0])

                                # 3. Alıcının anahtarıyla TEKRAR ŞİFRELE (Rubric #11)
                                tekrar_sifreli = des_sifrele(cozulmus_mesaj, alici_anahtari)

                                # 4. Alıcıya gönder
                                aktif_istemciler[alici].send(f"GELEN|{kullanici_adi}|{tekrar_sifreli}".encode())
                        except Exception as e:
                            print(f"Gönderme hatası: {e}")
                            del aktif_istemciler[alici]
                    else:
                        # ALICI OFFLINE İSE: Veritabanına kaydet
                        conn.execute("INSERT INTO mesajlar (gonderen, alici, mesaj) VALUES (?, ?, ?)",
                                     (kullanici_adi, alici, cozulmus_mesaj))
                        conn.commit()
                        print(f"[OFFLINE] {alici} yok, mesaj kaydedildi.")

                conn.close()

    except Exception as e:
        print(f"Hata: {e}")
    finally:
        if kullanici_adi and kullanici_adi in aktif_istemciler:
            del aktif_istemciler[kullanici_adi]
        try:
            client_socket.close()
        except:
            pass


def sunucuyu_baslat():
    veritabani_hazirla()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 12345))
    server.listen(10)
    print("SUNUCU AKTIF (Kapatmak icin Ctrl+C)...")

    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=istemciyi_dinle, args=(client, addr)).start()
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    sunucuyu_baslat()