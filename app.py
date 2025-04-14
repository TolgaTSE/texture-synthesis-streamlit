import streamlit as st
from PIL import Image, ImageOps

st.title("Doku Desen Üretme Uygulaması")
st.write("Yüklediğiniz resmi orijinal olarak koruyarak, diğer 3 alternatif deseni üreteceğiz.")
      
# Görüntü yükleme bileşeni
uploaded_file = st.file_uploader("Resim dosyanızı seçin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    # Resmi aç ve görüntüle
    image = Image.open(uploaded_file)
    st.image(image, caption="Orijinal Resim", use_column_width=True)
    
    # Kullanıcıdan boyut bilgilerini alma (varsayılan orijinal boyut)
    st.write("Resmin boyutlarını seçin (varsayılan: orijinal boyut)")
    real_width = st.number_input("Genişlik (piksel)", min_value=10, value=image.width)
    real_height = st.number_input("Yükseklik (piksel)", min_value=10, value=image.height)
    
    # Gerekirse resmi yeniden boyutlandırma
    if real_width != image.width or real_height != image.height:
        image = image.resize((real_width, real_height))
    
    if st.button("Desenleri Üret"):
        # Üç farklı alternatif deseni oluşturma:
        # 1. Yatay olarak ters çevirme (mirror) → Sol-sağ simetri
        horizontal_flip = ImageOps.mirror(image)
        # 2. Dikey olarak ters çevirme (flip) → Üst-alt simetri
        vertical_flip = ImageOps.flip(image)
        # 3. Hem yatay hem dikey ters çevirme: horizontal_flip sonrasında dikey flip yapılır.
        both_flip = ImageOps.flip(horizontal_flip)
        
        # Oluşturulan desenleri listeye ekleyelim
        images = [image, horizontal_flip, vertical_flip, both_flip]
        captions = [
            "Orijinal",
            "Yatay Çevirilmiş (Sol-Sağ)",
            "Dikey Çevirilmiş (Üst-Alt)",
            "Hem Yatay Hem Dikey Çevirilmiş"
        ]
        
        st.write("Üretilen Görseller:")
        st.image(images, caption=captions, use_column_width=True)
