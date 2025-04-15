import streamlit as st
from diffusers import StableDiffusionInpaintPipeline
import torch
from PIL import Image, ImageDraw
import numpy as np

st.title("Deep Learning Outpainting App")
st.write(
    """
    Bu uygulamada, bir resim yükleyip kenarlara ek boşluklar belirleyeceksiniz. 
    Uygulama, orijinal resmi bozmadan genişletilmiş tuvali oluşturur ve 
    Stable Diffusion Inpainting ile boşlukları "doğal" bir şekilde doldurur.
    """
)

# 1. Resim Yükleme
uploaded_file = st.file_uploader("Resminizi yükleyin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    input_image = Image.open(uploaded_file).convert("RGB")
    st.image(input_image, caption="Orijinal Resim", use_column_width=True)
    
    # 2. Margin (boşluk) Miktarlarını Belirleme
    st.write("Lütfen eklemek istediğiniz boşluk miktarlarını (piksel cinsinden) girin:")
    margin_top = st.number_input("Üst Boşluk", value=50, min_value=0)
    margin_bottom = st.number_input("Alt Boşluk", value=50, min_value=0)
    margin_left = st.number_input("Sol Boşluk", value=50, min_value=0)
    margin_right = st.number_input("Sağ Boşluk", value=50, min_value=0)
    
    # 3. Yeni Tuval Oluşturma & Maske Üretimi
    orig_width, orig_height = input_image.size
    new_width = orig_width + margin_left + margin_right
    new_height = orig_height + margin_top + margin_bottom

    # Yeni tuvali, orijinal resmin medyan renk değerine göre dolduralım.
    img_np = np.array(input_image)
    median_color = tuple(np.median(img_np.reshape(-1, 3), axis=0).astype(np.uint8))
    extended_image = Image.new("RGB", (new_width, new_height), median_color)
    # Orijinal resmi, genişletilmiş tuvalin ortasına yerleştiriyoruz.
    extended_image.paste(input_image, (margin_left, margin_top))
    
    # Maske: Orijinal resmin yer aldığı alan siyah (0), diğer yerler beyaz (255)
    mask = Image.new("L", (new_width, new_height), 255)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((margin_left, margin_top, margin_left + orig_width, margin_top + orig_height), fill=0)
    
    st.image(extended_image, caption="Genişletilmiş Tuval (Başlangıç)", use_column_width=True)
    st.image(mask, caption="Maske", use_column_width=True)
    
    # 4. Prompt Girişi
    prompt = st.text_input("Outpainting için prompt girin", "continue the scene naturally")
    
    # 5. Model Yükleme & Outpainting İşlemi
    if st.button("Outpaint Uygula"):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        st.write(f"Model {device} üzerinde çalışıyor...")
        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            "stabilityai/stable-diffusion-inpainting",
            revision="fp16",
            torch_dtype=torch.float16,
        )
        pipe = pipe.to(device)
        
        with torch.autocast(device):
            result = pipe(prompt=prompt, image=extended_image, mask_image=mask)
        outpainted_image = result.images[0]
        
        st.image(outpainted_image, caption="Outpainted Image", use_column_width=True)
