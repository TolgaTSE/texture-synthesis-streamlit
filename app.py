import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("Uncropping App - Continue Your Design")

st.write(
    """
    Bu uygulamada, bir resim yükleyip ek kenar boşlukları (margin) belirleyeceksiniz. 
    Uygulama, orijinal resmi dokusu korunmuş şekilde eklenen boşluklara "outpaint" yani 
    tasarımın devamı şeklinde doldurur. (Not: Bu basit prototip, küçük boşluklar için daha iyi sonuç verir.)
    """
)

# Kullanıcıdan resim yüklemesini isteyelim
uploaded_file = st.file_uploader("Resminizi Yükleyin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Orijinal Resim", use_column_width=True)
    
    # Orijinal resmin boyut bilgileri
    img_np = np.array(image)
    h, w, _ = img_np.shape
    
    st.write("Eklemek istediğiniz boşluk (margin) miktarlarını girin (piksel):")
    margin_top = st.number_input("Üst boşluk", min_value=0, value=50)
    margin_bottom = st.number_input("Alt boşluk", min_value=0, value=50)
    margin_left = st.number_input("Sol boşluk", min_value=0, value=50)
    margin_right = st.number_input("Sağ boşluk", min_value=0, value=50)
    
    # Yeni tuval boyutunu hesaplayalım
    new_width = w + margin_left + margin_right
    new_height = h + margin_top + margin_bottom
    
    if st.button("Uncrop ve Doldur"):
        # Arka plan için orijinal resmin medyan rengi (daha tutarlı sonuçlar için)
        median_color = np.median(img_np.reshape(-1, 3), axis=0).astype(np.uint8)
        # Yeni tuvali medyan renkle dolduruyoruz
        new_canvas = np.full((new_height, new_width, 3), median_color, dtype=np.uint8)
        
        # Orijinal resmi, belirlenen marginlere göre yeni tuvale yerleştiriyoruz
        new_canvas[margin_top:margin_top + h, margin_left:margin_left + w] = img_np
        
        # Maskeyi oluşturuyoruz: Yeni tuvalde, orijinal resmin yeri hariç tüm alanlar inpaint edilecek
        mask = np.ones((new_height, new_width), dtype=np.uint8) * 255  # 255: doldurulması gereken alan
        mask[margin_top:margin_top + h, margin_left:margin_left + w] = 0  # 0: orijinal resim alanı
        
        # OpenCV inpainting: Telea algoritması ile maskelenmiş alanı dolduruyoruz
        inpainted = cv2.inpaint(new_canvas, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        
        result_image = Image.fromarray(inpainted)
        st.image(result_image, caption="Uncropped ve Doldurulmuş Görüntü", use_column_width=True)
