import streamlit as st
import cv2
import numpy as np
from PIL import Image
import random

def synthesize_texture(input_image, out_width, out_height, patch_size=50):
    """
    Basit patch-tabana dayalı doku sentezi algoritması:
    - Girdi görüntüsünden rastgele patch'ler (parçalar) seçip,
    - Belirlenen output boyutlarında (out_width x out_height)
      yeni bir görüntü oluşturur.
    
    Not: Bu algoritma, gelişmiş "image quilting" yöntemlerine göre çok basittir.
    """
    # Girdi görüntüsünü numpy array'e çeviriyoruz
    input_img = np.array(input_image)
    h, w, c = input_img.shape

    # Çıkış görüntüsü için boş bir tuval oluşturuyoruz
    output_img = np.zeros((out_height, out_width, c), dtype=np.uint8)

    # Gerekli patch sayısını hesaplayalım
    num_patches_y = out_height // patch_size + 1
    num_patches_x = out_width // patch_size + 1

    # Her patch için:
    for i in range(num_patches_y):
        for j in range(num_patches_x):
            # Girdi görüntüsünden rastgele bir patch seçelim
            rand_y = random.randint(0, h - patch_size)
            rand_x = random.randint(0, w - patch_size)
            patch = input_img[rand_y:rand_y + patch_size, rand_x:rand_x + patch_size, :]

            # Çıkış görüntüsünde patch'in yerleştirileceği koordinatlar
            start_y = i * patch_size
            start_x = j * patch_size
            end_y = min(start_y + patch_size, out_height)
            end_x = min(start_x + patch_size, out_width)

            # Patch boyutlarını çıkış tuvaline uyacak şekilde kesiyoruz
            patch_cropped = patch[:end_y - start_y, :end_x - start_x, :]

            # Patch'i yerleştiriyoruz
            output_img[start_y:end_y, start_x:end_x, :] = patch_cropped

    return output_img

# Streamlit arayüzü
st.title("Doğal Taş Desen Sentez Uygulaması")
st.write("Bir doğal taş (ör. mermer, çimento, beton, ahşap vb.) görseli yükleyin ve desenin doğal geçişini taklit eden 4 yeni görsel üretelim.")

# Görüntü yükleme bileşeni
uploaded_file = st.file_uploader("Resim dosyanızı seçin", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Yüklenen Resim", use_column_width=True)

    # Gerçek boyut bilgilerini alma (varsayılan olarak yüklenen resmin boyutlarını kullanıyoruz)
    st.write("Resmin gerçek boyutlarını girin:")
    real_width = st.number_input("Genişlik (piksel)", min_value=10, value=image.width)
    real_height = st.number_input("Yükseklik (piksel)", min_value=10, value=image.height)

    if st.button("Desenleri Üret"):
        # Kullanıcının girdiği ebatlara göre görüntüyü yeniden boyutlandırma (gerekirse)
        image = image.resize((real_width, real_height))
        
        generated_images = []  # 4 yeni görseli saklamak için liste
        for k in range(4):
            new_texture = synthesize_texture(image, real_width, real_height, patch_size=50)
            generated_images.append(new_texture)

        st.write("Oluşturulan Yeni Görseller:")
        # Her bir üretilen görseli gösteriyoruz
        for idx, result in enumerate(generated_images):
            st.image(result, caption=f"Görsel {idx + 1}", use_column_width=False)
