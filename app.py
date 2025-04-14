import streamlit as st
import cv2
import numpy as np
from PIL import Image
import random

def min_error_boundary_cut(overlap_existing, overlap_new):
    """
    Verilen iki overlap bölge için (örneğin, soldaki veya üstteki) dinamik programlama ile
    minimum hata sınır kesme (seam carving benzeri) yapar. 
    Basitleştirilmiş bu örnekte, overlap bölgesindeki pikseller arasındaki kare hata farkını
    hesaplayıp, her satır (ya da sütun) için minimum hata seam’i buluyoruz.
    
    Bu fonksiyon, overlap_new için bir mask döndürür: mask = 1 olan bölgeler yeni patch'ten,
    mask = 0 olan bölgeler mevcut çıktıdan alınır.
    
    overlap_existing, overlap_new: (H x W x 3) float32 array'ler.
    Dönen mask: (H x W) float32, [0,1] aralığında.
    """
    # H x W boyutunda hatayı hesaplayalım (örn. kare fark toplamı, renk farkı)
    error = np.sum((overlap_existing - overlap_new) ** 2, axis=2)
    H, W = error.shape
    # Dinamik programlama: cost matrisi
    cost = np.zeros_like(error)
    cost[0] = error[0]
    backtrack = np.zeros_like(error, dtype=np.int32)

    # Örneğin, dikey seam (soldaki overlap için) uygulayalım:
    for i in range(1, H):
        for j in range(W):
            if j == 0:
                idx = np.argmin(cost[i-1, j:j+2])
                backtrack[i, j] = idx + j
                min_cost = cost[i-1, idx + j]
            elif j == W - 1:
                idx = np.argmin(cost[i-1, j-1:j+1])
                backtrack[i, j] = idx + j - 1
                min_cost = cost[i-1, idx + j - 1]
            else:
                idx = np.argmin(cost[i-1, j-1:j+2])
                backtrack[i, j] = idx + j - 1
                min_cost = cost[i-1, idx + j - 1]
            cost[i, j] = error[i, j] + min_cost

    # En düşük maliyetli seam'i arka takibe göre çekelim
    seam_mask = np.ones((H, W), dtype=np.float32)
    j = np.argmin(cost[-1])
    seam_mask[-1, :j] = 0
    seam_mask[-1, j:] = 1
    for i in range(H - 2, -1, -1):
        j = backtrack[i+1, j]
        seam_mask[i, :j] = 0
        seam_mask[i, j:] = 1

    return seam_mask

def quilt_texture(input_img, out_width, out_height, patch_size, overlap):
    """
    Image quilting algoritması:
    - input_img: Girdi texture (H x W x 3), numpy array (uint8)
    - out_width, out_height: Çıkış görüntüsünün boyutları
    - patch_size: Kullanılacak patch boyutu (kare)
    - overlap: Her patch arasında kullanılacak örtüşme boyutu
    """
    input_h, input_w, _ = input_img.shape
    # Çıkış görüntüsünü oluştur
    output = np.zeros((out_height, out_width, 3), dtype=np.uint8)

    # Kaç tane patch yerleştirileceğini belirleyelim
    step = patch_size - overlap
    n_patches_y = (out_height - patch_size) // step + 1
    n_patches_x = (out_width - patch_size) // step + 1

    for i in range(n_patches_y):
        for j in range(n_patches_x):
            y = i * step
            x = j * step

            # İlk patchi rastgele seç
            if i == 0 and j == 0:
                rand_y = random.randint(0, input_h - patch_size)
                rand_x = random.randint(0, input_w - patch_size)
                patch = input_img[rand_y:rand_y+patch_size, rand_x:rand_x+patch_size].copy()
                output[y:y+patch_size, x:x+patch_size] = patch
            else:
                # Aday patchler arasından seçim için belli sayıda deneme (örn. 20)
                candidates = []
                errors = []
                num_candidates = 20
                for k in range(num_candidates):
                    rand_y = random.randint(0, input_h - patch_size)
                    rand_x = random.randint(0, input_w - patch_size)
                    candidate = input_img[rand_y:rand_y+patch_size, rand_x:rand_x+patch_size].copy()
                    error = 0
                    if j > 0:  # soldaki örtüşme
                        existing = output[y:y+patch_size, x:x+overlap].astype(np.float32)
                        cand_overlap = candidate[:, :overlap].astype(np.float32)
                        error += np.sum((existing - cand_overlap) ** 2)
                    if i > 0:  # üstteki örtüşme
                        existing = output[y:y+overlap, x:x+patch_size].astype(np.float32)
                        cand_overlap = candidate[:overlap, :].astype(np.float32)
                        error += np.sum((existing - cand_overlap) ** 2)
                    candidates.append(candidate)
                    errors.append(error)
                best_idx = np.argmin(errors)
                patch = candidates[best_idx].copy()

                # Şimdi, eğer solda veya üstte örtüşme varsa, seam hesapla ve patch'i harmanla.
                blended = patch.copy().astype(np.float32)
                if j > 0:
                    # Soldaki overlap için
                    existing = output[y:y+patch_size, x:x+overlap].astype(np.float32)
                    patch_overlap = patch[:, :overlap].astype(np.float32)
                    seam_mask = min_error_boundary_cut(existing, patch_overlap)  # (patch_size x overlap)
                    # Seam mask'i genişletip soldaki kısmı harmanla
                    for r in range(patch_size):
                        blended[r, :overlap] = seam_mask[r, :] * patch_overlap[r] + (1 - seam_mask[r, :]) * existing[r]
                if i > 0:
                    # Üstteki overlap için
                    existing = output[y:y+overlap, x:x+patch_size].astype(np.float32)
                    patch_overlap = patch[:overlap, :].astype(np.float32)
                    seam_mask = min_error_boundary_cut(existing.T, patch_overlap.T).T  # transpoze ederek yatay seam hesapladık
                    for c in range(patch_size):
                        blended[:overlap, c] = seam_mask[:, c] * patch_overlap[:, c] + (1 - seam_mask[:, c]) * existing[:, c]

                # Yerleştirme: sadece non-overlap bölgeyi doğrudan kopyala, overlap kısımları harmanlandı
                output[y:y+patch_size, x:x+patch_size] = blended.clip(0,255).astype(np.uint8)

    return output

# Streamlit arayüzü
st.title("Photoshop Kalitesinde Texture Sentezi")
st.write(
    """
    Bu uygulama, yüklediğiniz doğal taş/doku görüntüsü üzerinden gelişmiş image quilting algoritması kullanarak
    Photoshop kalitesinde (kesintisiz, doğallıkta) yeni bir doku görüntüsü sentezler.
    Lütfen girdi resminizi ve istediğiniz çıkış boyutlarını, patch ve overlap boyutlarını girin.
    """
)
uploaded_file = st.file_uploader("Görüntü Dosyanızı Seçin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    input_pil = Image.open(uploaded_file).convert("RGB")
    input_img = np.array(input_pil)
    st.image(input_pil, caption="Girdi Görüntü", use_column_width=True)
    
    out_width = st.number_input("Çıkış Görüntü Genişliği (piksel)", min_value=50, value=input_pil.width)
    out_height = st.number_input("Çıkış Görüntü Yüksekliği (piksel)", min_value=50, value=input_pil.height)
    patch_size = st.number_input("Patch Boyutu (piksel)", min_value=10, value=50)
    overlap = st.number_input("Örtüşme Boyutu (piksel)", min_value=1, value=10)
    
    if st.button("Yeni Görüntüyü Üret"):
        output_img = quilt_texture(input_img, out_width, out_height, patch_size, overlap)
        output_pil = Image.fromarray(output_img)
        st.image(output_pil, caption="Oluşturulan Görüntü", use_column_width=True)
