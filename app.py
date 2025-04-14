import streamlit as st
from PIL import Image, ImageOps

st.title("Tam Blok Tasarım Üretme Uygulaması")
st.write(
    """
    Yüklediğiniz görüntü, tam bir blok tasarımın bir parçası (quadrant) olarak kabul edilecek.
    Diğer üç parçayı, uygun aynalama işlemleriyle üreterek, 2x2'lik tam blok tasarımı elde edeceğiz.
    """
)

# Görüntü yükleme bileşeni
uploaded_file = st.file_uploader("Görüntünüzü seçin (jpg, jpeg, png):", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Yüklenen görüntüyü açıyoruz.
    quadrant = Image.open(uploaded_file)
    st.image(quadrant, caption="Yüklenen Parça (Quadrant)", use_column_width=True)
    
    # Görüntünün boyutlarını alalım
    w, h = quadrant.size
    st.write(f"Görüntü Boyutu: {w} x {h} piksel")
    
    # Dilerseniz, görüntüyü yeniden boyutlandırmak için boyut girişi alabilirsiniz.
    # (Varsayılan olarak yüklenen görüntünün boyutunu kullanıyoruz.)
    new_width = st.number_input("Yeni Genişlik (piksel)", min_value=10, value=w)
    new_height = st.number_input("Yeni Yükseklik (piksel)", min_value=10, value=h)
    
    if new_width != w or new_height != h:
        quadrant = quadrant.resize((new_width, new_height))
        w, h = quadrant.size
        st.image(quadrant, caption="Yeniden Boyutlandırılmış Parça", use_column_width=True)
    
    if st.button("Tam Blok Tasarımını Üret"):
        # Varsayalım ki yüklenen parça, blok tasarımın sol üst kısmını temsil ediyor.
        # Diğer parçaları aynalama (flip) işlemleri ile üretelim.
        # Q1: Sol üst (orijinal)
        Q1 = quadrant
        # Q2: Sağ üst için; orijinalin yatay aynası
        Q2 = ImageOps.mirror(quadrant)
        # Q3: Sol alt için; orijinalin dikey aynası
        Q3 = ImageOps.flip(quadrant)
        # Q4: Sağ alt için; hem yatay hem dikey aynalama uygulanmış (çapraz)
        Q4 = ImageOps.flip(Q2)  # ya da ImageOps.mirror(Q3)
        
        # Üst satırı oluştur: Q1 ve Q2'nin yan yana eklenmesi
        top_row = Image.new('RGB', (w * 2, h))
        top_row.paste(Q1, (0, 0))
        top_row.paste(Q2, (w, 0))
        
        # Alt satırı oluştur: Q3 ve Q4'ün yan yana eklenmesi
        bottom_row = Image.new('RGB', (w * 2, h))
        bottom_row.paste(Q3, (0, 0))
        bottom_row.paste(Q4, (w, 0))
        
        # Tam blok (2x2) tasarımını oluşturmak için üst ve alt satırları alt alta ekleyin
        full_block = Image.new('RGB', (w * 2, h * 2))
        full_block.paste(top_row, (0, 0))
        full_block.paste(bottom_row, (0, h))
        
        # Oluşturulan tam blok tasarımını ekrana getirin
        st.image(full_block, caption="Tam Blok Tasarımı", use_column_width=True)
        
        # İsterseniz, diğer üç parçayı ayrı ayrı da gösterebilirsiniz:
        st.write("Diğer Üç Parça:")
        st.image([Q2, Q3, Q4], caption=[
            "Sağ Üst Parça (Yatay Aynası)", 
            "Sol Alt Parça (Dikey Aynası)", 
            "Sağ Alt Parça (Çapraz - Hem Yatay Hem Dikey Aynalama)"
        ], width=w)
