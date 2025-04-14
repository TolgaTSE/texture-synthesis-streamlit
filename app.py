import streamlit as st
from PIL import Image
import numpy as np

# Oturumda eğitim sonucu stilini saklamak için
if 'trained_style' not in st.session_state:
    st.session_state['trained_style'] = None

# Kullanıcıya hangi aşamada çalışmak istediğini soralım.
stage = st.selectbox("Hangi Aşamayı Yapmak İstersiniz?",
                       ["Eğitim (Training) Aşaması", "Yeni Face Üretim (Generation) Aşaması"])

if stage == "Eğitim (Training) Aşaması":
    st.header("Eğitim Aşaması")
    st.write("Lütfen önce eğitim için bir referans görüntü, ardından üç adet farklı 'face' resmini yükleyin. "
             "Bu resimler, sistemin kendini eğitmesi için kullanılacaktır.")
    
    # Eğitim referans görüntüsü
    train_ref_file = st.file_uploader("Eğitim Referans Görüntünüzü Seçin", type=["jpg", "jpeg", "png"], key="train_ref")
    if train_ref_file is not None:
        train_ref_img = Image.open(train_ref_file).convert("RGB")
        st.image(train_ref_img, caption="Eğitim Referans Görüntü", use_column_width=True)
    else:
        st.info("Lütfen eğitim referans görüntüsünü yükleyin.")
    
    # Üç adet face resmi
    face1_file = st.file_uploader("Face Resmi 1", type=["jpg", "jpeg", "png"], key="face1")
    face2_file = st.file_uploader("Face Resmi 2", type=["jpg", "jpeg", "png"], key="face2")
    face3_file = st.file_uploader("Face Resmi 3", type=["jpg", "jpeg", "png"], key="face3")
    
    if face1_file and face2_file and face3_file:
        face_img1 = Image.open(face1_file).convert("RGB")
        face_img2 = Image.open(face2_file).convert("RGB")
        face_img3 = Image.open(face3_file).convert("RGB")
        
        # Eğer eğitim referans yüklendiyse, face resimlerini onun boyutuna göre yeniden boyutlandırıyoruz
        if train_ref_file is not None:
            target_size = train_ref_img.size
        else:
            target_size = face_img1.size  # veya face_img1'in boyutunu kullanabilirsiniz
        
        face_img1 = face_img1.resize(target_size)
        face_img2 = face_img2.resize(target_size)
        face_img3 = face_img3.resize(target_size)
        
        # Üç face resminin piksel bazında ortalamasını alıyoruz
        np_face1 = np.array(face_img1).astype(np.float32)
        np_face2 = np.array(face_img2).astype(np.float32)
        np_face3 = np.array(face_img3).astype(np.float32)
        avg_face = (np_face1 + np_face2 + np_face3) / 3.0
        avg_face = np.clip(avg_face, 0, 255).astype(np.uint8)
        trained_style = Image.fromarray(avg_face)
        
        # Eğitim sonucu stilde oluşan görüntüyü oturumda saklıyoruz
        st.session_state['trained_style'] = trained_style
        
        st.image(trained_style, caption="Eğitim Sonucu - Ortak Stil", use_column_width=True)
        st.success("Eğitim tamamlandı. Lütfen 'Yeni Face Üretim (Generation) Aşaması'na geçin.")
    else:
        st.info("Lütfen üç adet face resmini de yükleyin.")

elif stage == "Yeni Face Üretim (Generation) Aşaması":
    st.header("Yeni Face Üretim Aşaması")
    if st.session_state['trained_style'] is None:
        st.error("Öncelikle Eğitim Aşamasını tamamlayın!")
    else:
        st.write("Yeni face üretmek için, istenilen referans görüntüyü yükleyin. "
                 "Sistem, eğitim aşamasında elde ettiği ortak stili bu referansa uygulayarak yeni bir yüz üretecek.")
        
        gen_ref_file = st.file_uploader("Yeni Referans Görüntüyü Seçin", type=["jpg", "jpeg", "png"], key="gen_ref")
        if gen_ref_file is not None:
            gen_ref_img = Image.open(gen_ref_file).convert("RGB")
            st.image(gen_ref_img, caption="Yeni Referans Görüntü", use_column_width=True)
            
            # Yeni referans ve eğitim sonucu stilinin boyutunu eşleyelim
            target_size = gen_ref_img.size
            trained_style = st.session_state['trained_style'].resize(target_size)
            
            # Basit bir blend işlemi ile yeni yüz üretimi:
            # Çıktı = alpha * yeni referans + (1 - alpha) * eğitim stili
            # Burada örneğin alpha = 0.5 kullanılarak eşit ağırlıkta karışım elde ediliyor.
            alpha = 0.5
            np_gen = np.array(gen_ref_img).astype(np.float32)
            np_style = np.array(trained_style).astype(np.float32)
            blended = (alpha * np_gen + (1 - alpha) * np_style)
            blended = np.clip(blended, 0, 255).astype(np.uint8)
            output_img = Image.fromarray(blended)
            
            st.image(output_img, caption="Üretilen Yeni Face", use_column_width=True)
