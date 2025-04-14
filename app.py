import streamlit as st
import cv2
import numpy as np
from PIL import Image
import random

def min_error_boundary_cut(overlap_existing, overlap_new):
    """
    İki overlap bölge (örneğin, soldaki veya üstteki) için dinamik programlama ile 
    minimum hata sınır kesme (seam carving benzeri) yapar. 
    Bu fonksiyon, overlap_new için bir mask döndürür: mask = 1 olan bölgeler yeni patch'ten,
    mask = 0 olan bölgeler mevcut çıktının korunacağı yerlerdir.
    overlap_existing ve overlap_new boyutları (H x W x 3) olmalıdır.
    Dönen seam_mask boyutu: (H x W) float32
    """
    error = np.sum((overlap_existing - overlap_new) ** 2, axis=2)
    H, W = error.shape
    cost = np.zeros_like(error)
    cost[0] = error[0]
    backtrack = np.zeros_like(error, dtype=np.int32)

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
    output = np.zeros((out_height, out_width, 3), dtype=np.uint8)

    step = patch_size - overlap
    n_patches_y = (out_height - patch_size) // step + 1
    n_patches_x = (out_width - patch_size) // step + 1

    for i in range(n_patches_y):
        for j in range(n_patches_x):
            y = i * step
            x = j * step

            # İlk patchi rastgele seç (sol üst köşe)
            if i == 0 and j == 0:
                rand_y = random.randint(0, input_h - patch_size)
                rand_x = random.randint(0, input_w - patch_size)
                patch = input_img[rand_y:rand_y+patch_size, rand_x:rand_x+patch_size].copy()
                output[y:y+patch_size, x:x+patch_size] = patch
            else:
                candidates = []
                errors = []
                num_candidates = 20
                for k in range(num_candidates):
                    rand_y = random.randint(0, input_h - patch_size)
                    rand_x = random.randint(0, input_w - patch_size)
                    candidate = input_img[rand_y:rand_y+patch_size, rand_x:rand_x+patch_size].copy()
                    error = 0
                    # Soldaki overlap hata hesaplaması (varsa)
                    if j > 0:
                        actual_overlap = min(overlap, out_width - x)
                        existing_left = output[y:y+patch_size, x:x+actual_overlap].astype(np.float32)
                        cand_left = candidate[:, :actual_overlap].astype(np.float32)
                        error += np.sum((existing_left - cand_left) ** 2)
                    # Üstteki overlap hata hesaplaması (varsa)
                    if i > 0:
                        actual_overlap_v = min(overlap, out_height - y)
                        existing_top = output[y:y+actual_overlap_v, x:x+patch_size].astype(np.float32)
                        cand_top = candidate[:actual_overlap_v, :].astype(np.float32)
                        error += np.sum((existing_top - cand_top) ** 2)
                    candidates.append(candidate)
                    errors.append(error)
                best_idx = np.argmin(errors)
                patch = candidates[best_idx].copy()
                blended = patch.copy().astype(np.float32)

                # Soldaki overlap (yatay seam) varsa:
                if j > 0:
                    actual_overlap = min(overlap, out_width - x)
                    existing_left = output[y:y+patch_size, x:x+actual_overlap].astype(np.float32)
                    cand_left = patch[:, :actual_overlap].astype(np.float32)
                    seam_mask = min_error_boundary_cut(existing_left, cand_left)  # shape: (patch_size, actual_overlap)
                    # Her satır için seam mask uygulaması
                    for r in range(patch_size):
                        factor = seam_mask[r, :].reshape(-1, 1)  # (actual_overlap, 1)
                        blended[r, :actual_overlap] = factor * cand_left[r] + (1 - factor) * existing_left[r]

                # Üstteki overlap (dikey seam) varsa:
                if i > 0:
                    actual_overlap_v = min(overlap, out_height - y)
                    existing_top = output[y:y+actual_overlap_v, x:x+patch_size].astype(np.float32)
                    cand_top = patch[:actual_overlap_v, :].astype(np.float32)
                    seam_mask = min_error_boundary_cut(existing_top.T, cand_top.T).T  # shape: (actual_overlap_v, patch_size)
                    for c in range(patch_size):
                        factor = seam_mask[:, c].reshape(-1, 1)  # (actual_overlap_v, 1)
                        blended[:actual_overlap_v, c] = factor * cand_top[:, c] + (1 - factor) * existing_top[:, c]

                output[y:y+patch_size, x:x+patch_size] = blended.clip(0, 255).astype(np.uint8)

    return output

# Streamlit Arayüzü
st.title("Photoshop Kalitesinde Texture Sentezi")
st.write(
    """
    Bu uygulama, yüklediğiniz doğal taş/doku görüntüsü üzerinden gelişmiş image quilting algoritması kullanarak
    Photoshop kalitesinde (kesintisiz, doğallıkta) yeni bir doku görüntüsü sentezler.
    Lütfen girdi resminizi ve istediğiniz çıkış boyutlarını, patch boyutunu ve örtüşme boyutunu girin.
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
