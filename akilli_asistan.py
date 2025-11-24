import os
import time
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image
import pytesseract
from sentence_transformers import SentenceTransformer
import chromadb

# --- AYARLAR VE ÖN YÜKLEME ---
# 1. Tesseract'ın kurulu olduğu yer (Windows kullanıyorsanız burayı kendi yolunuza göre düzenleyin!)
# Mac/Linux kullanıyorsanız bu satırı yoruma alabilirsiniz.
try:
    # Bu yol, PyInstaller ile uygulama yapılırken hata verebilir. Test aşamasında kullanın.
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except Exception:
    # Eğer bu satır hata verirse ve Tesseract PATH'te ekliyse, bu normaldir.
    pass

# Klasör yolları, GUI ile doldurulacaktır. Başlangıçta boş kalabilir.
TAKIP_EDILEN_KLASOR = ""
HEDEF_KLASOR = ""

# 2. Semantik Model ve Veritabanı Tanımları
try:
    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2') 
    client = chromadb.Client()
    COLLECTION_NAME = "kategori_anlamlari"
    collection = client.get_or_create_collection(COLLECTION_NAME)
except Exception as e:
    print(f"UYARI: Yapay Zeka kütüphaneleri yüklenemedi: {e}")
    print("Lütfen 'pip install sentence-transformers chromadb' komutunu çalıştırdığınızdan emin olun.")
    sys.exit()


# --- GENİŞLETİLMİŞ KATEGORİ TANIMLARI (Semantik Veri Seti) ---
KATEGORI_ORNEKLERI = {
    "Finans_Ekonomi": [
        "Banka dekontları, IBAN ve Swift kodları, kredi kartı ekstreleri.",
        "Aylık bütçe planlaması, yatırım portföyü, hisse senedi takibi.",
        "Ödeme hatırlatıcıları, Vadesi gelen faturalar, KDV hesaplamaları."
    ],
    "Yazilim_Kodlama": [
        "Python, JavaScript, SQL gibi programlama dillerinde kod blokları ve örnekler.",
        "Hata mesajları, 'Traceback' veya 'SyntaxError' gibi konsol çıktıları.",
        "API belgeleri, sunucu ayarları, Linux komut satırı çıktıları.",
        "Veri bilimi, makine öğrenimi, yapay zeka ve algoritma konuları."
    ],
    "Akademik_Egitim": [
        "Ders notları, üniversite ödev başlıkları, araştırma makaleleri ve tezler.",
        "Matematik formülleri, bilimsel grafikler, tarihi tarihler ve isimler.",
        "Eğitim platformlarından alınan ders özetleri veya sınav soruları."
    ],
    "Saglik_Yasam": [
        "Doktor randevusu, e-reçete, kullanılan ilaçların isimleri.",
        "Tahlil sonuçları, kan değerleri, check-up raporları ve hastalık isimleri.",
        "Spor antrenman programları, diyet listeleri, kalori takibi ve beslenme bilgileri."
    ],
    "Medya_Eglence": [
        "Film ve dizi önerileri, izleme listeleri, oyuncu isimleri ve eleştirileri.",
        "Spotify veya YouTube çalma listeleri, müzik sözleri, konser biletleri.",
        "Oyun stratejileri, Twitch yayın notları, sosyal medya postları ve komik sözler."
    ],
    "Idari_Belgeler": [
        "E-Devlet çıktıları, resmi dilekçe taslakları, başvuru formları.",
        "Pasaport veya kimlik kartı bilgileri, ikametgah belgeleri, noter ve vekaletname.",
        "Vergi beyannameleri, sigorta poliçeleri ve yasal sözleşmeler."
    ],
    "Alisveris_Urun": [
        "Online mağaza sepeti içerikleri, indirim kuponu kodları, kampanya görselleri.",
        "Garanti belgesi, ürün kullanım kılavuzu, teknik özellikler ve ürün incelemeleri.",
        "Kargo takip numaraları, teslimat adresleri, iade ve değişim bilgileri."
    ],
    "Seyahat_Lojistik": [
        "Uçak, otobüs, tren bileti bilgileri, PNR ve koltuk numaraları.",
        "Otel veya Airbnb rezervasyonları, konaklama adresleri ve harita görüntüleri.",
        "Navigasyon rotaları, toplu taşıma saatleri, seyahat planları ve vize bilgileri."
    ]
}


def veritabani_olustur(ornekler):
    """Kategori örneklerini vektöre çevirir ve ChromaDB'ye kaydeder."""
    ids = []
    documents = []
    metadatas = []

    # Veritabanını her çalıştırmada yeniden oluşturmak için temizle
    try:
        client.delete_collection(COLLECTION_NAME)
        global collection 
        collection = client.get_or_create_collection(COLLECTION_NAME)
    except Exception:
        pass

    for kategori, cumleler in ornekler.items():
        for i, cumle in enumerate(cumleler):
            ids.append(f"{kategori}_{i}")
            documents.append(cumle)
            metadatas.append({"kategori": kategori})

    # Örnek cümleleri vektöre çevir (Yapay Zeka İşlemi)
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"✅ Vektör Veritabanı başarıyla oluşturuldu. Toplam {len(documents)} kayıt var.")


def klasor_secme_arayuzu():
    """Kullanıcıdan takip ve hedef klasörlerini seçmesini isteyen arayüzü başlatır."""
    
    global takip_klasoru, hedef_klasoru
    takip_klasoru = ""
    hedef_klasoru = ""
    
    def klasor_sec(tip):
        klasor_yolu = filedialog.askdirectory()
        if klasor_yolu:
            if tip == "takip":
                global takip_klasoru
                takip_klasoru = klasor_yolu
                takip_etiketi.config(text="Takip Edilen: " + klasor_yolu)
            elif tip == "hedef":
                global hedef_klasoru
                hedef_klasoru = klasor_yolu
                hedef_etiketi.config(text="Hedef Arşiv: " + klasor_yolu)

    def baslat():
        if not takip_klasoru or not hedef_klasoru:
            messagebox.showerror("Hata", "Lütfen hem takip hem de hedef klasörü seçin!")
            return
        
        pencere.destroy()

    pencere = tk.Tk()
    pencere.title("Akıllı Asistan Ayarları")
    pencere.geometry("500x250")

    tk.Label(pencere, text="1. Ekran Görüntülerinin Düştüğü Klasör:", font=('Arial', 10)).pack(pady=5)
    tk.Button(pencere, text="Klasör Seç", command=lambda: klasor_sec("takip")).pack()
    takip_etiketi = tk.Label(pencere, text="Takip Edilen: Seçilmedi", fg="blue")
    takip_etiketi.pack(pady=5)

    tk.Frame(pencere, height=1, bg="gray").pack(fill='x', padx=10, pady=5)
    
    tk.Label(pencere, text="2. Düzenlenmiş Dosyaların Gideceği Klasör:", font=('Arial', 10)).pack(pady=5)
    tk.Button(pencere, text="Klasör Seç", command=lambda: klasor_sec("hedef")).pack()
    hedef_etiketi = tk.Label(pencere, text="Hedef Arşiv: Seçilmedi", fg="blue")
    hedef_etiketi.pack(pady=5)

    tk.Button(pencere, text="Asistanı Başlat", command=baslat, bg="green", fg="white", font=('Arial', 12, 'bold')).pack(pady=20)

    pencere.mainloop()
    
    return takip_klasoru, hedef_klasoru


class DosyaIsleyici(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        dosya_yolu = event.src_path
        dosya_adi = os.path.basename(dosya_yolu)
        
        if not dosya_adi.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            return

        print(f"\n👀 Yeni dosya algılandı: {dosya_adi}")
        time.sleep(1) # Dosyanın tamamen kaydedilmesi için bekle
        
        try:
            self.analiz_et_ve_tasi(dosya_yolu, dosya_adi)
        except Exception as e:
            print(f"❌ Hata oluştu ({dosya_adi}): {e}. Dosya taşınamadı.")

    def analiz_et_ve_tasi(self, dosya_yolu, dosya_adi):
        # 1. Resmi Aç ve Oku (OCR)
        try:
            resim = Image.open(dosya_yolu)
            metin = pytesseract.image_to_string(resim, lang='tur+eng')
            metin = metin.strip().lower()
            if not metin:
                raise ValueError("Resimde okunabilir metin bulunamadı.")
        except Exception:
            metin = "metin yok"
        
        # 2. Kategoriyi Semantik Olarak Bul
        bulunan_kategori = "Diger"
        
        if metin != "metin yok":
            try:
                sorgu_vektor = model.encode([metin]).tolist()

                sonuclar = collection.query(
                    query_embeddings=sorgu_vektor,
                    n_results=1 
                )

                if sonuclar and sonuclar['metadatas'] and sonuclar['metadatas'][0]:
                    bulunan_kategori = sonuclar['metadatas'][0][0]['kategori']
                    benzerlik_skoru = sonuclar['distances'][0][0] 
                    
                    print(f"💡 Semantik Eşleşme: {bulunan_kategori}. Skor (Uzaklık): {benzerlik_skoru:.4f}")
            except Exception as e:
                print(f"Semantik Analiz Hatası: {e}. 'Diger'e taşınıyor.")
                bulunan_kategori = "Diger"
        else:
            print("❗ Resimde metin yok. 'Diger'e taşınıyor.")
            

        # 3. ve 4. Klasör Oluşturma ve Taşıma
        kategori_yolu = os.path.join(HEDEF_KLASOR, bulunan_kategori)
        if not os.path.exists(kategori_yolu):
            os.makedirs(kategori_yolu)

        tarih_damgasi = time.strftime("%Y%m%d_%H%M%S")
        
        # Dosya adını ilk 20 karakter ve tarih damgası ile oluştur
        yeni_ad_oneki = metin[:20].replace('\n', ' ').replace(':', '_').strip() or "EkranGoruntusu"
        yeni_dosya_adi = f"{bulunan_kategori}_{yeni_ad_oneki}_{tarih_damgasi}.png"
        
        yeni_dosya_yolu = os.path.join(kategori_yolu, yeni_dosya_adi)
        
        # Dosyayı taşı
        shutil.copy2(dosya_yolu, yeni_dosya_yolu)
        os.remove(dosya_yolu)

        print(f"✅ Dosya taşındı: {yeni_dosya_yolu}\n")


if __name__ == "__main__":
    
    # 1. Kullanıcı Arayüzünden Yolları Al
    TAKIP_EDILEN_KLASOR, HEDEF_KLASOR = klasor_secme_arayuzu()
    
    if not TAKIP_EDILEN_KLASOR or not HEDEF_KLASOR:
        print("Klasör seçimi yapılmadığı için program sonlandırıldı.")
        sys.exit()

    print("-" * 50)
    print(f"Takip Edilen Klasör: {TAKIP_EDILEN_KLASOR}")
    print(f"Hedef Klasör: {HEDEF_KLASOR}")
    print("-" * 50)

    # 2. Veritabanını Başlat
    veritabani_olustur(KATEGORI_ORNEKLERI)
    
    # 3. Watchdog Gözlemcisi Başlat
    event_handler = DosyaIsleyici()
    observer = Observer()
    observer.schedule(event_handler, TAKIP_EDILEN_KLASOR, recursive=False)
    observer.start()

    print(f"\n🚀 Akıllı Asistan (Semantik) Çalışıyor... '{TAKIP_EDILEN_KLASOR}' izleniyor.")
    print("Programı durdurmak için lütfen bu terminal penceresini kapatın veya Ctrl+C tuşlarına basın.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()