# Steganografi ve Kriptografi Tabanlı Güvenli Mesajlaşma Sistemi

Bu proje, görüntü içine veri gizleme (**LSB Steganography**) ve simetrik şifreleme (**DES Cryptography**) yöntemlerini birleştirerek uçtan uca güvenli ve çevrimdışı (offline) mesajlaşmaya olanak tanıyan bir istemci-sunucu (Client-Server) uygulamasıdır.

## 🚀 Proje Mimarisi ve Çalışma Mantığı

Sistem, bir merkezi sunucu ve bu sunucuya bağlanan birden fazla istemciden oluşur. Temel güvenlik mimarisi iki aşamalıdır:

### 1. Kayıt ve Kimlik Doğrulama (LSB)
* **İstemci Tarafı:** Kullanıcı kayıt olurken bir kullanıcı adı, parola ve resim seçer. Yazılım, parolayı **LSB (Least Significant Bit)** yöntemiyle seçilen resmin piksellerine gizler.
* **Sunucu Tarafı:** Sunucuya iletilen resimdeki gizli anahtar çözülür ve kullanıcı adı ile eşleştirilerek veritabanına kaydedilir. Bu anahtar, ileride yapılacak DES şifrelemeleri için temel oluşturur.



### 2. Mesajlaşma Süreci (DES & Çift Şifreleme)
* **Gönderim (C1):** Mesaj, gönderenin kendi anahtarı (parolası) ile **DES** algoritması kullanılarak şifrelenir ve sunucuya iletilir.
* **Sunucu Rölesi:** Sunucu gelen mesajı C1'in anahtarıyla deşifre eder. Ardından mesajın içeriğini alıcının (C2) anahtarıyla tekrar şifreleyerek C2'nin mesaj kutusuna (Offline Box) kaydeder.
* **Alım (C2):** Kullanıcı online olduğunda, sunucudan kendisine gelen şifreli mesajı alır ve kendi yerel anahtarıyla deşifre ederek orijinal içeriğe ulaşır.



## 🛠 Kullanılan Teknolojiler
* **Dil:** Python 3.x
* **Arayüz:** Tkinter (GUI)
* **Ağ Protokolü:** TCP/IP (Socket)
* **Veritabanı:** SQLite3
* **Kütüphaneler:** * `Pillow` (Görüntü işleme)
  * `pycryptodome` (DES Şifreleme)
  * `socket` & `threading` (Ağ iletişimi)

## 📦 Kurulum ve Çalıştırma

1. **Gerekli Kütüphaneleri Yükleyin:**
   ```bash
   pip install Pillow pycryptodome
