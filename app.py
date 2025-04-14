import streamlit as st
from PIL import Image, ImageEnhance
import random

def get_random_patch(img, patch_size):
    """
    Referans görüntüden, belirlenen patch boyutunda rastgele bir bölge seçer.
    """
    img_width, img_height = img.size
    p_w, p_h = patch_size
    max_x = img_width - p_w
    max_y = img_height - p_h
    left = random.randint(0, max(0, max_x))
    top = random.randint(0, max(0, max_y))
    patch = img.crop((left, top, left + p_w, top + p_h))
    return patch

def center_crop(image, target_size):
    """
    Eğer dönüşüm sonucu patch boyutları değiştiyse, 
    ortadan istenilen boyuta (target_size) kırpar.
    """
    target_w, target_h = target_size
    w, h = image.size
    left = (w - target_w) // 2
    top = (h - target_h) // 2
    return image.crop((left, top, left + target_w, top + target_h))

def apply_random_transform(patch, variation, target_size):
    """
    Verilen patch üzerinde, kullanıcı tarafından belirlenen yüzde (variation)
    oranında rastgele dönüşümler (örn. rotation, brightness değişikliği) uygular.
    Ardından, dönüşüm sonucu oluşan boyut farklılıklarını ortadan kaldırmak için
    merkeze kırparak target_size boyutuna getirir.
    """
    # Rastgele açı: variation değeri ne kadar yüksekse, dönüş açısı da o kadar geniş olur.
    angle = random.uniform(-variation/2, variation/2)
    patch_rotated = patch.rotate(angle, expand=True)
    
    # Rastgele brightness (parlaklık) değişikliği:
    brightness_factor = 1 + random.uniform(-variation/100, variation/100)
    enhancer = ImageEnhance.Brightness(patch_rotated)
    patch_bright = enhancer.enhance(brightness_factor)
    
    # Dönüşüm sonrası patch boyutu değişmiş olabilir; center crop ile istenilen boyuta getiriyoruz.
    patch_final = center_crop(patch_bright, target_size)
    return patch_final

st.title("Derin Doku Sentezi ile Yeni Tasarım Üretme")
st.write(
    """
    Referans görüntünüzü kullanarak, ürünün çizgilerinin farklı bölümlerinden 
    alınmış gibi, referans tasarıma benzemeyen tamamen yeni bir doku sentezi tasarımı üretiyoruz.
    """
)

# Görüntü yükleme bölümü
uploaded_file = st.file_uploader("Görüntünüzü seçin (jpg, jpeg, png):", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    reference_image = Image.open(uploaded_file).convert("RGB")
    st.image(reference_image, caption="Referans Görüntü", use_column_width=True)
    
    # Referans görüntü boyutunu gösterelim.
    ref_w, ref_h = reference_image.size
    st.write(f"Referans Görüntü Boyutu: {ref_w} x {ref_h} piksel")
    
    # Kullanıcıdan yeni tasarımın boyutlarını alalım.
    out_width = st.number_input("Yeni Tasarım Genişliği (piksel)", min_value=50, value=ref_w)
    out_height = st.number_input("Yeni Tasarım Yüksekliği (piksel)", min_value=50, value=ref_h)
    
    # Kullanıcıya varyasyon oranını (yüzde) soralım.
    variation = st.slider("Fark Yüzdesi (0-100)", 0, 100, 50)
    
    if st.button("Yeni Tasarımı Üret"):
        # Ürün tasarımımızı 2x2'lik bir mozayik (mosaic) şeklinde oluşturacağız.
        # Her patch, çıkış görüntüsünün yarısının boyutunda olacak.
        patch_size = (out_width // 2, out_height // 2)
        
        patches = []
        for i in range(4):
            # Referans görüntünün farklı bölümlerinden rastgele patch seçimi:
            patch = get_random_patch(reference_image, patch_size)
            # Kullanıcının belirttiği varyasyon oranında, rastgele dönüşüm uygula:
            transformed_patch = apply_random_transform(patch, variation, patch_size)
            patches.append(transformed_patch)
        
        # Yeni tasarım görüntüsü oluşturuluyor.
        output_image = Image.new("RGB", (patch_size[0] * 2, patch_size[1] * 2))
        # 2x2 düzeninde patch’leri yerleştir:
        output_image.paste(patches[0], (0, 0))
        output_image.paste(patches[1], (patch_size[0], 0))
        output_image.paste(patches[2], (0, patch_size[1]))
        output_image.paste(patches[3], (patch_size[0], patch_size[1]))
        
        st.image(output_image, caption="Yeni Derin Doku Sentezi Tasarımı", use_column_width=True)
