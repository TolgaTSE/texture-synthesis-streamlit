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
    mask = 0 olan bölgeler mevcut çıktının alınacağı yerlerdir.
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
                    if j > 0:  # Soldaki örtüşme
                        existing = output[y:y+patch_size, x:x+overlap].astype(np.float32)
                        cand_overlap = candidate[:, :overlap].astype(np.float32)
                        error += np.sum((existing - cand_overlap) ** 2)
                    if i > 0:  # Üstteki örtüşme
                        existing = output[y:y+overlap, x:x+patch_size].astype(np.float32)
                        cand_overlap = candidate[:overlap, :].astype(np.float32)
                        error += np.sum((existing - cand_overlap) ** 2)
                    candidates.append(candidate)
                    errors.append(error)
                best_idx = np.argmin(errors)
                patch = candidates[best_idx].copy()

                blended = patch.copy().astype(np.float32)
                if j > 0:
                    # Soldaki overlap için seam blending
                    existing = output[y:y+patch_size, x:x+overlap].astype(np.float32)
                    patch_overlap = patch[:, :overlap].astype(np.float32)
                    seam_mask = min_error_boundary_cut(existing, patch_overlap)  # shape: (patch_size, overlap)
                    for r in range(patch_size):
                        factor = seam_mask[r, :].reshape(-1, 1)  # Yeniden şekillendiriyoruz: (overlap, 1)
                        blended[r, :overlap] = factor * patch_overlap[r] + (1 - factor) * existing[r]
                if i > 0:
                    # Üstteki overlap için seam blending
                    existing = output[y:y+overlap, x:x+patch_size].astype(np.float32)
                    patch_overlap = patch[:overlap, :].astype(np.float32)
                    seam_mask = min_error_boundary_cut(existing.T, patch_overlap.T).T  # shape: (overlap, patch_size)
                    for c in range(patch_size):
                        factor = seam_mask[:, c].reshape(-1, 1)  # (overlap, 1)
                        blended[:overlap, c] = factor * patch_overlap[:, c] + (1 - factor_*
