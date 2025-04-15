import streamlit as st
import PIL.Image
from PIL import ImageCms
import numpy as np
import os
from pathlib import Path

# Eğer PIL.ImageCms modülünde INTENT sabitleri tanımlı değilse, manuel olarak tanımlıyoruz.
if not hasattr(ImageCms, "INTENT_PERCEPTUAL"):
    ImageCms.INTENT_PERCEPTUAL = 0
if not hasattr(ImageCms, "INTENT_RELATIVE_COLORIMETRIC"):
    ImageCms.INTENT_RELATIVE_COLORIMETRIC = 1
if not hasattr(ImageCms, "INTENT_SATURATION"):
    ImageCms.INTENT_SATURATION = 2
if not hasattr(ImageCms, "INTENT_ABSOLUTE_COLORIMETRIC"):
    ImageCms.INTENT_ABSOLUTE_COLORIMETRIC = 3

def apply_icc_profile(image_path, icc_path):
    """Apply ICC profile to image"""
    try:
        # Open the image
        img = PIL.Image.open(image_path)
        
        # Ensure image is in RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Load ICC profile if provided
        if icc_path:
            input_profile = ImageCms.getOpenProfile(icc_path)
            output_profile = ImageCms.createProfile('sRGB')
            
            # İlk olarak INTENT_PERCEPTUAL ile dönüşümü deniyoruz
            try:
                transform = ImageCms.buildTransformFromOpenProfiles(
                    input_profile, output_profile, 'RGB', 'RGB',
                    renderingIntent=ImageCms.INTENT_PERCEPTUAL
                )
            except Exception as e:
                st.warning(f"INTENT_PERCEPTUAL ile dönüşüm kurulamadı: {str(e)}. INTENT_RELATIVE_COLORIMETRIC ile deneniyor.")
                transform = ImageCms.buildTransformFromOpenProfiles(
                    input_profile, output_profile, 'RGB', 'RGB',
                    renderingIntent=ImageCms.INTENT_RELATIVE_COLORIMETRIC
                )
            
            # Apply the transformation
            img = ImageCms.applyTransform(img, transform)
            
        return img
    except Exception as e:
        st.error(f"Error applying ICC profile: {str(e)}")
        return None

def apply_lighting_condition(img, temperature, brightness):
    """Apply lighting condition to image"""
    try:
        # Convert to numpy array
        img_array = np.array(img).astype(float)
        
        # Temperature adjustment (basit yaklaşımla)
        temperature_factor = (temperature - 5000) / 5000  # 5000K civarında normalize edilir
        
        # RGB kanallarında ayarlama
        img_array[:,:,0] *= (1 + 0.2 * temperature_factor)  # Kırmızı
        img_array[:,:,2] *= (1 - 0.2 * temperature_factor)  # Mavi
        
        # Brightness (parlaklık) ayarlaması
        img_array *= brightness
        
        # Değerleri 0-255 aralığında kısıtla
        img_array = np.clip(img_array, 0, 255)
        
        # Tekrar uint8 formatına çevir
        img_array = img_array.astype(np.uint8)
        
        return PIL.Image.fromarray(img_array)
    except Exception as e:
        st.error(f"Error applying lighting condition: {str(e)}")
        return None

def main():
    st.title("Tile Lighting Simulator")
    
    # Dosya yükleyiciler
    image_file = st.file_uploader("Upload Tile Image (TIFF)", type=['tiff', 'tif'])
    icc_file = st.file_uploader("Upload ICC Profile", type=['icc'])
    
    # Aydınlatma kontrolleri
    temperature = st.slider("Color Temperature (K)", 2700, 6500, 5000)
    brightness = st.slider("Brightness", 0.5, 1.5, 1.0)
    
    if image_file and icc_file:
        # Yüklenen dosyaları geçici olarak kaydet
        temp_image_path = "temp_image.tiff"
        temp_icc_path = "temp_icc.icc"
        
        with open(temp_image_path, "wb") as f:
            f.write(image_file.getbuffer())
        with open(temp_icc_path, "wb") as f:
            f.write(icc_file.getbuffer())
            
        # Görüntüyü işle
        try:
            # ICC profilini uygula
            img_with_icc = apply_icc_profile(temp_image_path, temp_icc_path)
            
            if img_with_icc:
                # Aydınlatma koşulunu uygula
                final_img = apply_lighting_condition(img_with_icc, temperature, brightness)
                
                if final_img:
                    # Sonuçları göster
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Original Image")
                        st.image(img_with_icc)
                    with col2:
                        st.subheader("Adjusted Image")
                        st.image(final_img)
                        
                    # İşlenmiş görüntü için indirme butonu ekle
                    if st.button("Download Processed Image"):
                        final_img.save("processed_image.png")
                        with open("processed_image.png", "rb") as file:
                            st.download_button(
                                label="Download Image",
                                data=file,
                                file_name="processed_image.png",
                                mime="image/png"
                            )
        
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            
        # Geçici dosyaları temizle
        try:
            os.remove(temp_image_path)
            os.remove(temp_icc_path)
        except:
            pass

if __name__ == "__main__":
    main()
