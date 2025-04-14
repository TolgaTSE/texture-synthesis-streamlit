import streamlit as st
from PIL import Image
import cv2
import numpy as np

def generate_variant(image, diff_percent):
    """
    Verilen görüntü üzerinde, diff_percent parametresi kadar maksimum yer değiştirme
    (displacement) uygulayarak yeni bir varyant üretir.
    Bu işlem, görüntüdeki yapısal detayları biraz rastgele kaydırır;
    dolayısıyla renkler korunurken, doku ve desen detaylarında istenen fark ortaya çıkar.
    """
    # PIL görüntüyü numpy array'e çeviriyoruz.
    img = np.array(image)
    
    # Görüntü boyutlarını alıyoruz.
    h, w = img.shape[:2]
    
    # Her piksel için koordinat ızgarası oluşturuyoruz.
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    x = x.astype(np.float32)
    y = y.astype(np.float32)
    
    # Maksimum kayma (max displacement) piksel cinsinden:
    # Örneğin, diff_percent=100 için maksimum 10 piksel kayma uygulanacak.
    max_disp = diff_percent / 100 * 10
    
    # Rastgele x ve y kaymaları oluşturuyoruz.
    random_dx = np.random.uniform(-max_disp, max_disp, size=(h, w)).astype(np.float32)
    random_dy = np.random.uniform(-max_disp, max_disp, size=(h, w)).astype(np.float32)
    
    # Yeni koordinat haritalarını hesaplıyoruz.
    map_x = (x + random_dx).clip(0, w - 1)
    map_y = (y + random_dy).clip(0, h - 1)
    
    # OpenCV'nin remap fonksiyonu ile görüntüyü yeni koordinatlara göre yeniden yapılandırıyoruz.
    variant = cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR)
    return Image.fromarray(variant)

st.title("Tam Blok Tasarım Üretme Uygulaması (Modifiye Desen)")
st.write(
    """
    Referans görüntüyü kullanarak, farklılık oranına bağlı olarak üç alternatif varyant (desen)
    üreteceğiz. Renkler aynı kalırken; doku, damar, desen detaylarında, vermek istediğiniz
    yüzde kadar fark olacak.
    """
)

# Görüntü yükleme bölümü
uploaded_file = st.file_uploader("Görüntünüzü seçin (jpg, jpeg, png):", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    base_image = Image.open(uploaded_file).convert("RGB")
    st.image(base_image, caption="Referans Görüntü", use_column_width=True)

    # Orijinal boyutları alalım.
    w, h = base_image.size
    st.write(f"Görüntü Boyutu: {w} x {h} piksel")
    
    # Gerekirse görüntüyü yeniden boyutlandırma (isteğe bağlı)
    new_width = st.number_input("Yeni Genişlik (piksel)", min_value=10, value=w)
    new_height = st.number_input("Yeni Yükseklik (piksel)", min_value=10, value=h)
    if new_width != w or new_height != h:
        base_image = base_image.resize((new_width, new_height))
        w, h = base_image.size
        st.image(base_image, caption="Yeniden Boyutlandırılmış Görüntü", use_column_width=True)
    
    # Kullanıcı, referans görüntü ile diğer varyant arasındaki fark yüzdesini belirlesin.
    diff_percent = st.slider("Fark Yüzdesi (0-100)", min_value=0, max_value=100, value=20, step=1)
    
    if st.button("Tam Blok Tasarımını Üret"):
        # Referans görüntü sabit, diğer varyantlar için generate_variant fonksiyonu kullanılıyor.
        Q1 = base_image  # Orijinal referans
        Q2 = generate_variant(base_image, diff_percent)
        Q3 = generate_variant(base_image, diff_percent)
        Q4 = generate_variant(base_image, diff_percent)
        
        # 2x2'lik tam blok tasarımı oluşturmak için yeni büyük bir görüntü oluşturup,
        # dört varyantı belirtilen koordinatlara yapıştırıyoruz.
        block_width = new_width * 2
        block_height = new_height * 2
        
        full_block = Image.new('RGB', (block_width, block_height))
        full_block.paste(Q1, (0, 0))
        full_block.paste(Q2, (new_width, 0))
        full_block.paste(Q3, (0, new_height))
        full_block.paste(Q4, (new_width, new_height))
        
        st.image(full_block, caption="Tam Blok Tasarımı", use_column_width=True)
        
        st.write("Üretilen Varyant Görseller:")
        st.image([Q1, Q2, Q3, Q4],
                 caption=["Referans", "Varyant 1", "Varyant 2", "Varyant 3"],
                 use_column_width=True)
