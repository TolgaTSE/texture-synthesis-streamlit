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

def manual_icc_conversion(img):
    """
    Fallback olarak, ICC dönüşümü oluşturulamadığında
    RGB kanallarında sabit ölçekli düzeltme uygular.
    """
    try:
        st.info("ICC dönüşümü oluşturulamadı, manuel RGB düzeltmesi uygulanıyor.")
        arr = np.array(img).astype(float)
        # Örnek düzeltme faktörleri: CMYK'dan RGB dönüşümde oluşabilecek farkları yakalamak için
        correction = np.array([0.98, 1.0, 1.02])  # Kırmızı, Yeşil, Mavi
        arr[:,:,0] *= correction[0]
        arr[:,:,1] *= correction[1]
        arr[:,:,2] *= correction[2]
        arr = np.clip(arr, 0, 255)
        return PIL.Image.fromarray(arr.astype(np.uint8))
    except Exception as e:
        st.error(f"Manual ICC dönüşüm hatası: {str(e)}")
        return img

def apply_icc_profile(image_path, icc_path):
    """
    ICC profilini uygulayarak görüntüdeki renk dönüşümünü yapar.
    - Görüntü CMYK ise, otomatik olarak CMYK -> sRGB dönüşümü için gerekli adım uygulanır.
    - ICC profil dosyası yoksa ve görüntü CMYK ise, ImageCms.createProfile() ile varsayılan CMYK profili kullanılır.
    - Dönüşüm, önce INTENT_PERCEPTUAL, hata alınırsa INTENT_RELATIVE_COLORIMETRIC ile denenir.
    - Her iki yöntem de başarısız olursa, manuel kanal düzeltmesi (fallback) kullanılır.
    """
    try:
        img = PIL.Image.open(image_path)
        
        # Dönüştürülecek input renk modu (varsayılan 'RGB')
        input_mode = "RGB"
        
        # Eğer görüntü CMYK ise, input_mode'u "CMYK" olarak ayarla
        if img.mode == "CMYK":
            input_mode = "CMYK"
        elif img.mode != "RGB":
            # Diğer renk modlarında da öncelikle RGB'ye çevir
            img = img.convert('RGB')
        
        # ICC dönüşümü için input profili: eğer kullanıcı tarafından ICC dosyası yüklendiyse onu kullan,
        # değilse; eğer görüntü CMYK ise varsayılan bir CMYK profili oluştur.
        if icc_path:
            input_profile = ImageCms.getOpenProfile(icc_path)
        elif input_mode == "CMYK":
            input_profile = ImageCms.createProfile("CMYK")
        else:
            # ICC profili yoksa ve görüntü zaten RGB ise, dönüşüm gerekmez.
            return img
        
        # Her zaman sRGB'ye dönüşüm yapıyoruz.
        output_profile = ImageCms.createProfile('sRGB')
        
        transform = None
        # Önce INTENT_PERCEPTUAL ile dönüşüm dene
        try:
            transform = ImageCms.buildTransformFromOpenProfiles(
                input_profile, output_profile, input_mode, 'RGB',
                renderingIntent=ImageCms.INTENT_PERCEPTUAL
            )
        except Exception as e1:
            st.warning(f"INTENT_PERCEPTUAL ile dönüşüm kurulamadı: {str(e1)}. INTENT_RELATIVE_COLORIMETRIC ile deneniyor.")
            try:
                transform = ImageCms.buildTransformFromOpenProfiles(
                    input_profile, output_profile, input_mode, 'RGB',
                    renderingIntent=ImageCms.INTENT_RELATIVE_COLORIMETRIC
                )
            except Exception as e2:
                st.warning(f"INTENT_RELATIVE_COLORIMETRIC ile dönüşüm kurulamadı: {str(e2)}. Manuel dönüşüm uygulanacak.")
                transform = None
        
        # Eğer geçerli bir dönüşüm elde edilebildiyse, uyguluyoruz; aksi halde fallback dönüşüm
        if transform is not None:
            img = ImageCms.applyTransform(img, transform)
        else:
            img = manual_icc_conversion(img)
            
        return img
        
    except Exception as e:
        st.error(f"Error applying ICC profile: {str(e)}")
        return None

def apply_lighting_condition(img, temperature, brightness):
    """Renk sıcaklığı ve parlaklık ayarını uygular."""
    try:
        img_array = np.array(img).astype(float)
        
        # Basit sıcaklık ayarlaması: 5000K etrafında normalize
        temperature_factor = (temperature - 5000) / 5000
        
        # RGB kanallarında ayarlama: sıcaklık farkına göre kırmızı ve mavi kanallar ayarlanıyor.
        img_array[:,:,0] *= (1 + 0.2 * temperature_factor)  # Kırmızı
        img_array[:,:,2] *= (1 - 0.2 * temperature_factor)  # Mavi
        
        # Parlaklık ayarlaması
        img_array *= brightness
        img_array = np.clip(img_array, 0, 255)
        img_array = img_array.astype(np.uint8)
        return PIL.Image.fromarray(img_array)
    except Exception as e:
        st.error(f"Error applying lighting condition: {str(e)}")
        return None

def main():
    st.title("Tile Lighting Simulator")
    
    # Dosya yükleyici alanlar
    image_file = st.file_uploader("Upload Tile Image (TIFF)", type=['tiff', 'tif'])
    icc_file = st.file_uploader("Upload ICC Profile", type=['icc'])
    
    # Renk sıcaklığı ve parlaklık kontrolleri
    temperature = st.slider("Color Temperature (K)", 2700, 6500, 5000)
    brightness = st.slider("Brightness", 0.5, 1.5, 1.0)
    
    if image_file:
        # Yüklenen dosyaları geçici olarak kaydet
        temp_image_path = "temp_image.tiff"
        with open(temp_image_path, "wb") as f:
            f.write(image_file.getbuffer())
        
        # ICC dosyası yüklendiyse yolunu al, aksi halde boş bırakıyoruz.
        temp_icc_path = None
        if icc_file:
            temp_icc_path = "temp_icc.icc"
            with open(temp_icc_path, "wb") as f:
                f.write(icc_file.getbuffer())
        
        # Görüntü işleme
        try:
            # ICC profil dönüşümü uygula; eğer ICC dosyası yoksa, CMYK görüntülerde otomatik dönüşüm yapılacak.
            img_with_icc = apply_icc_profile(temp_image_path, temp_icc_path)
            
            if img_with_icc:
                final_img = apply_lighting_condition(img_with_icc, temperature, brightness)
                if final_img:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Original / ICC Dönüştürülmüş Image")
                        st.image(img_with_icc)
                    with col2:
                        st.subheader("Adjusted Image")
                        st.image(final_img)
                    
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
        
        # Geçici dosyaları sil
        try:
            os.remove(temp_image_path)
            if temp_icc_path:
                os.remove(temp_icc_path)
        except Exception:
            pass

if __name__ == "__main__":
    main()
