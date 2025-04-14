import streamlit as st
from PIL import Image
import numpy as np

# Session state'de model saklamak için alan oluşturuyoruz.
if 'model' not in st.session_state:
    st.session_state['model'] = None

# Kullanıcıya hangi aşamada çalışmak istediğini soralım:
phase = st.selectbox("Lütfen yapmak istediğiniz aşamayı seçin:", 
                       ["Eğitim (Training) Aşaması", "Yeni Face Üretim (Generation) Aşaması"])

###############################################
# AŞAMA 1: EĞİTİM (TRAINING) AŞAMASI
###############################################

if phase == "Eğitim (Training) Aşaması":
    st.header("Eğitim Aşaması: Model Oluşturma")
    st.write(
        """
        Lütfen **bir referans görüntü** yükleyin ve ardından 
        referans görüntüden türetilmiş **üç farklı face (desen) resmini** yükleyin.
        Bu resimler, referans ile karşılaştırıldığında hangi bölgelerde ve ne kadar farklılık olduğunu analiz edeceğiz.
        Hesaplanan ortalama fark haritası (model) daha sonra yeni face üretiminde kullanılacaktır.
        """
    )

    # Eğitim için referans görüntü yükleme
    train_ref_file = st.file_uploader("Eğitim Referans Görüntünüzü Yükleyin", type=["jpg", "jpeg", "png"], key="train_ref")
    
    # Üç adet face resmi yükleme
    face1_file = st.file_uploader("Face Resmi 1", type=["jpg", "jpeg", "png"], key="face1")
    face2_file = st.file_uploader("Face Resmi 2", type=["jpg", "jpeg", "png"], key="face2")
    face3_file = st.file_uploader("Face Resmi 3", type=["jpg", "jpeg", "png"], key="face3")
    
    if train_ref_file and face1_file and face2_file and face3_file:
        # Görüntüleri açalım ve RGB formatına çevirelim.
        train_ref_img = Image.open(train_ref_file).convert("RGB")
        face_img1 = Image.open(face1_file).convert("RGB")
        face_img2 = Image.open(face2_file).convert("RGB")
        face_img3 = Image.open(face3_file).convert("RGB")
        
        # Tüm face resimlerini, referans görüntünün boyutuna göre yeniden boyutlandırıyoruz.
        target_size = train_ref_img.size  # (width, height)
        face_img1 = face_img1.resize(target_size)
        face_img2 = face_img2.resize(target_size)
        face_img3 = face_img3.resize(target_size)
        
        # Kullanıcıya referans görüntüyü gösterelim.
        st.image(train_ref_img, caption="Eğitim Referans Görüntü", use_column_width=True)
        
        # Numpy dizilerine çeviriyoruz (float32 tipinde).
        ref_arr = np.array(train_ref_img).astype(np.float32)
        f1_arr = np.array(face_img1).astype(np.float32)
        f2_arr = np.array(face_img2).astype(np.float32)
        f3_arr = np.array(face_img3).astype(np.float32)
        
        # Her face için referanstan farkı hesaplıyoruz.
        diff1 = f1_arr - ref_arr
        diff2 = f2_arr - ref_arr
        diff3 = f3_arr - ref_arr
        
        # Model olarak, pixel bazında üç yüz arasındaki ortalama farkı ve standart sapmayı alıyoruz.
        mean_diff = np.mean([diff1, diff2, diff3], axis=0)
        std_diff = np.std([diff1, diff2, diff3], axis=0)
        
        # Modeli session_state'e kaydediyoruz.
        st.session_state['model'] = {
            'mean_diff': mean_diff,  # Ortalama fark haritası (pixel bazlı)
            'std_diff': std_diff,    # Farkın varyasyonu (standart sapma)
            'ref_size': target_size  # Kullanılan boyut bilgisi
        }
        
        st.success("Eğitim tamamlandı. Model oluşturuldu.")
        st.write("Model Özeti: Referans görüntü ile face resimleri arasındaki ortalama fark ve varyasyon hesaplandı.")
        
        # İsteğe bağlı: Ortalama farkı bir görselle incelemek isterseniz,
        # fark değerlerini 0-255 aralığına normallendirip görselleştirebilirsiniz.
        norm_mean_diff = (mean_diff - mean_diff.min()) / (mean_diff.max() - mean_diff.min() + 1e-5) * 255
        mean_diff_img = Image.fromarray(norm_mean_diff.astype(np.uint8))
        st.image(mean_diff_img, caption="Ortalama Fark Görüntüsü (Model)", use_column_width=True)
    else:
        st.info("Lütfen eğitim için referans ve 3 face resmini yükleyin.")

###############################################
# AŞAMA 2: YENİ FACE ÜRETİM (GENERATION) AŞAMASI
###############################################

elif phase == "Yeni Face Üretim (Generation) Aşaması":
    st.header("Yeni Face Üretim Aşaması")
    
    if st.session_state['model'] is None:
        st.error("Öncelikle Eğitim Aşamasını tamamlayıp modeli oluşturun!")
    else:
        st.write(
            """
            Model hazır! Şimdi, yeni face üretimi için referans görüntünüzü yükleyin.
            Eğitim aşamasında elde ettiğimiz fark modelini (ortalama fark + varyasyon) kullanarak,
            bu referansa benzer şekilde, farklı üç face üreteceğiz.
            """
        )
        
        gen_ref_file = st.file_uploader("Yeni Referans Görüntüyü Yükleyin", type=["jpg", "jpeg", "png"], key="gen_ref")
        if gen_ref_file is not None:
            gen_ref_img = Image.open(gen_ref_file).convert("RGB")
            # Yeni referans görüntüyü, modelin kaydedildiği boyuta getirelim.
            target_size = st.session_state['model']['ref_size']
            gen_ref_img = gen_ref_img.resize(target_size)
            st.image(gen_ref_img, caption="Yeni Referans Görüntü", use_column_width=True)
            
            model = st.session_state['model']
            mean_diff = model['mean_diff']
            std_diff = model['std_diff']
            
            new_faces = []
            # Üç yeni face üretmek için, her biri için rastgele varyasyon ekleyelim.
            for i in range(3):
                # Pixel bazlı rastgele gürültü; modelde hesaplanan standart sapma kullanılarak.
                noise = np.random.normal(loc=0.0, scale=std_diff, size=mean_diff.shape)
                # Yeni face = yeni referans + (ortalama fark + rastgele varyasyon)
                new_face_arr = np.array(gen_ref_img).astype(np.float32) + mean_diff + noise
                new_face_arr = np.clip(new_face_arr, 0, 255).astype(np.uint8)
                new_face = Image.fromarray(new_face_arr)
                new_faces.append(new_face)
                
            st.image(new_faces, caption=["Yeni Face 1", "Yeni Face 2", "Yeni Face 3"], use_column_width=True)
