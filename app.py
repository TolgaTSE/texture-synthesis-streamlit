import streamlit as st
from PIL import Image
import numpy as np
import cv2

# Fonksiyon: Kenar haritasını oluştur (edge layer)  
def get_edge(img):
    # Önce PIL görüntüyü numpy array'e çevir, ardından grayscale yapıp Canny ile kenarları çıkarıyoruz.
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, threshold1=100, threshold2=200)
    # Kenar haritasını 0-1 aralığına getiriyoruz
    edges = edges.astype(np.float32) / 255.0
    return edges

# Session state'de model bilgisini saklamak için
if 'model' not in st.session_state:
    st.session_state['model'] = None

# Kullanıcıya hangi aşamada işlem yapmak istediğini soralım.
phase = st.selectbox("Lütfen yapmak istediğiniz aşamayı seçin:", 
                       ["Eğitim (Training) Aşaması", "Yeni Face Üretim (Generation) Aşaması"])

###############################################
# AŞAMA 1: EĞİTİM (TRAINING) AŞAMASI
###############################################
if phase == "Eğitim (Training) Aşaması":
    st.header("Eğitim Aşaması: Model Oluşturma")
    st.write(
        """
        Lütfen **bir referans** görüntünüzü ve referans görüntüye göre türetilmiş **üç farklı face (desen) görüntüsünü** yükleyin.
        Bu aşamada her resmin renk katmanı ve kenar (edge) katmanlarındaki değişiklikleri analiz edip,
        referans ile arasındaki ortalama farkları (ve varyasyonu) öğrenip model olarak kaydedeceğiz.
        """
    )
    
    # Resim yüklemeleri
    train_ref_file = st.file_uploader("Eğitim Referans Görüntünüzü Yükleyin", type=["jpg", "jpeg", "png"], key="train_ref")
    face1_file = st.file_uploader("Face Resmi 1", type=["jpg", "jpeg", "png"], key="face1")
    face2_file = st.file_uploader("Face Resmi 2", type=["jpg", "jpeg", "png"], key="face2")
    face3_file = st.file_uploader("Face Resmi 3", type=["jpg", "jpeg", "png"], key="face3")
    
    if train_ref_file and face1_file and face2_file and face3_file:
        # Resimleri açalım, referans görüntüyü belirleyelim
        ref_img = Image.open(train_ref_file).convert("RGB")
        ref_size = ref_img.size  # (width, height)
        st.image(ref_img, caption="Referans Görüntü", use_column_width=True)
        
        # Diğer face resimlerini referans boyutuna göre yeniden boyutlandırıyoruz.
        face1 = Image.open(face1_file).convert("RGB").resize(ref_size)
        face2 = Image.open(face2_file).convert("RGB").resize(ref_size)
        face3 = Image.open(face3_file).convert("RGB").resize(ref_size)
        st.image([face1, face2, face3], caption=["Face 1", "Face 2", "Face 3"], use_column_width=True)
        
        # Numpy dizilerine çeviriyoruz (renk katmanı için)
        ref_arr = np.array(ref_img).astype(np.float32)
        f1_arr = np.array(face1).astype(np.float32)
        f2_arr = np.array(face2).astype(np.float32)
        f3_arr = np.array(face3).astype(np.float32)
        
        # Renk farklarını hesaplayalım: her face için referans görüntüden fark
        diff1 = f1_arr - ref_arr
        diff2 = f2_arr - ref_arr
        diff3 = f3_arr - ref_arr
        
        # Ortalama renk fark modelini oluşturuyoruz
        model_color_diff = (diff1 + diff2 + diff3) / 3.0
        
        # Kenar (edge) katmanları için;
        ref_edge = get_edge(ref_img)
        edge1 = get_edge(face1)
        edge2 = get_edge(face2)
        edge3 = get_edge(face3)
        diff_edge1 = edge1 - ref_edge
        diff_edge2 = edge2 - ref_edge
        diff_edge3 = edge3 - ref_edge
        
        # Ortalama edge fark modelini oluşturuyoruz
        model_edge_diff = (diff_edge1 + diff_edge2 + diff_edge3) / 3.0
        
        # Modeli session_state'e kaydediyoruz
        st.session_state['model'] = {
            'ref_size': ref_size,
            'color_diff': model_color_diff,
            'edge_diff': model_edge_diff
        }
        
        st.success("Eğitim tamamlandı. Model oluşturuldu.")
        
        # İsteğe bağlı: Modelin özetini görselleştirelim
        norm_color_diff = (model_color_diff - model_color_diff.min())
        norm_color_diff = norm_color_diff / (model_color_diff.max() - model_color_diff.min() + 1e-5) * 255
        norm_color_diff = norm_color_diff.astype(np.uint8)
        st.image(Image.fromarray(norm_color_diff), caption="Ortalama Renk Farkı (Model)")
        
        norm_edge_diff = (model_edge_diff - model_edge_diff.min())
        norm_edge_diff = norm_edge_diff / (model_edge_diff.max() - model_edge_diff.min() + 1e-5) * 255
        norm_edge_diff = norm_edge_diff.astype(np.uint8)
        st.image(Image.fromarray(norm_edge_diff), caption="Ortalama Kenar Farkı (Model)", use_column_width=True)
    else:
        st.info("Lütfen eğitim için referans ve 3 adet face görüntüsünü yükleyin.")

###############################################
# AŞAMA 2: YENİ FACE ÜRETİM (GENERATION) AŞAMASI
###############################################
elif phase == "Yeni Face Üretim (Generation) Aşaması":
    st.header("Yeni Face Üretim Aşaması")
    
    if st.session_state['model'] is None:
        st.error("Lütfen önce Eğitim Aşamasını tamamlayıp modeli oluşturun!")
    else:
        st.write(
            """
            Model hazır! Şimdi, yeni face üretmek için referans görüntünüzü yükleyin.
            Bu referans üzerinde, eğitimde elde edilen modeldeki (katman bazında renk ve kenar farkları)
            bilgileri uygulanarak, yeni ve birbirinden farklı 3 yüz (face) üretilecektir.
            """
        )
        
        gen_ref_file = st.file_uploader("Yeni Üretim İçin Referans Görüntüyü Yükleyin", type=["jpg", "jpeg", "png"], key="gen_ref")
        if gen_ref_file:
            gen_img = Image.open(gen_ref_file).convert("RGB")
            target_size = st.session_state['model']['ref_size']
            gen_img = gen_img.resize(target_size)
            st.image(gen_img, caption="Yeni Üretim Referansı", use_column_width=True)
            
            # Modelde kayıtlı renk ve kenar farkları
            model = st.session_state['model']
            color_diff = model['color_diff']
            edge_diff = model['edge_diff']
            
            gen_arr = np.array(gen_img).astype(np.float32)
            # Yeni üreteceğimiz yüzlerde farklılık oluşturmak için rastgele varyasyon ekleyelim
            new_faces = []
            for i in range(3):
                # Rastgele gürültü ekleyelim (renk ve edge için ayrı)
                noise_color = np.random.normal(loc=0.0, scale=5.0, size=gen_arr.shape)
                # Yeni renk katmanı: referans renk + modelden öğrenilen ortalama fark + gürültü
                new_color = gen_arr + color_diff + noise_color
                new_color = np.clip(new_color, 0, 255)
                new_color = new_color.astype(np.uint8)
                
                # Kenar katmanını hesaplayalım
                gen_edge = get_edge(gen_img)
                noise_edge = np.random.normal(loc=0.0, scale=0.05, size=gen_edge.shape)
                new_edge = gen_edge + edge_diff + noise_edge
                new_edge = np.clip(new_edge, 0, 1)
                
                # Kenar haritasını 3 kanallı hale getirelim
                new_edge_3ch = np.stack([new_edge]*3, axis=-1) * 255
                
                # Sonuçta, renk katmanı ile kenar detaylarını hafifçe harmanlayalım
                # (Örneğin %80 renk, %20 kenar)
                blended = 0.8 * new_color + 0.2 * new_edge_3ch
                blended = np.clip(blended, 0, 255).astype(np.uint8)
                new_face = Image.fromarray(blended)
                new_faces.append(new_face)
            
            st.image(new_faces, caption=["Yeni Face 1", "Yeni Face 2", "Yeni Face 3"], use_column_width=True)
