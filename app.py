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
    Fallback olarak, ICC dönüşümü oluşturulamadığında,
    RGB kanallarında sabit ölçekli yaklaşık düzeltme uygular.
    """
    try:
        st.info("ICC dönüşümü oluşturulamadı, manuel RGB düzeltmesi uygulanıyor.")
        arr = np.array(img).astype(float)
        # Örnek düzeltme faktörleri: Kırmızı, Yeşil, Mavi için
        correction = np.array([0.98, 1.0, 1.02])
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
    ICC profilini uygulayarak görüntüde renk dönüşümü yapar.
    - Eğer kaynak görüntü RGB değilse (örneğin CMYK veya başka), öncelikle RGB'ye dönüştürülür.
    - Sağlanan ICC profili kullanılarak dönüşüm, INTENT_PERCEPTUAL, hata alınırsa INTENT_RELATIVE_COLORIMETRIC ile denenir.
    - Her iki yöntem de başarısız olursa, manuel düzeltme (fallback) uygulanır.
    """
    try:
        img = PIL.Image.open(image_path)
        
        # WebP de dahil diğer formatlarda, görüntü modunun RGB olması beklenir.
        if img.mode != 'RGB':
            st.info(f"Görüntü modu {img.mode} olduğundan, RGB'ye dönüştürülüyor.")
            img = img.convert('RGB')
        
        # Eğer ICC profili sağlanmışsa dönüşüm işlemi yapılıyor.
        if icc_path:
            input_profile = ImageCms.getOpenProfile(icc_path)
            output_profile = ImageCms.createProfile('sRGB')
            
            transform = None
            # İlk olarak INTENT_PERCEPTUAL ile dönüşüm dene
            try:
                transform = ImageCms.buildTransformFromOpenProfiles(
                    input_profile, output_profile, 'RGB', 'RGB',
                    renderingIntent=ImageCms.INTENT_PERCEPTUAL
                )
            except Exception as e1:
                st.warning(f"INTENT_PERCEPTUAL ile dönüşüm kurulamadı: {str(e1)}. INTENT_RELATIVE_COLORIMETRIC ile deneniyor.")
                try:
                    transform = ImageCms.buildTransformFromOpenProfiles(
                        input_profile, output_profile, 'RGB', 'RGB',
                        renderingIntent=ImageCms.INTENT_RELATIVE_COLORIMETRIC
                    )
                except Exception as e2:
                    st.warning(f"INTENT_RELATIVE_COLORIMETRIC ile dönüşüm kurulamadı: {str(e2)}. Manuel dönüşüm uygulanacak.")
                    transform = None
            
            if transform is not None:
                img = ImageCms.applyTransform(img, transform)
            else:
                img = manual_icc_conversion(img)
                
        return img
        
    except Exception as e:
        st.error(f"Error applying ICC profile: {str(e)}")
        return None

def apply_lighting_condition(img, temperature, brightness):
    """
    Renk sıcaklığı (temperature) ve parlaklık (brightness) ayarını uygular.
    Basit bir yaklaşım ile kırmızı ve mavi kanallarda ayarlamalar yapılır.
    """
    try:
        img_array = np.array(img).astype(float)
        
        # Basit sıcaklık ayarlaması: 5000K etrafında normalize
        temperature_factor = (temperature - 5000) / 5000
        
        # Kırmızı (artış) ve Mavi (azalış) kanalları ayarlanıyor
        img_array[:,:,0] *= (1 + 0.2 * temperature_factor)
        img_array[:,:,2] *= (1 - 0.2 * temperature_factor)
        
        # Parlaklık ayarı
        img_array *= brightness
        img_array = np.clip(img_array, 0, 255)
        img_array = img_array.astype(np.uint8)
        
        return PIL.Image.fromarray(img_array)
    except Exception as e:
        st.error(f"Error applying lighting condition: {str(e)}")
        return None

def main():
    st.title("Tile Lighting Simulator")
    
    # Kaynak resimler için dosya yükleyici: WebP, TIFF ve TIF uzantıları destekleniyor
    image_file = st.file_uploader("Upload Tile Image (WEBP/TIFF)", type=['webp', 'tiff', 'tif'])
    icc_file = st.file_uploader("Upload ICC Profile", type=['icc'])
    
    # Renk sıcaklığı ve parlaklık kontrolleri
    temperature = st.slider("Color Temperature (K)", 2700, 6500, 5000)
    brightness = st.slider("Brightness", 0.5, 1.5, 1.0)
    
    if image_file:
        # Yüklenen resim dosyasını geçici olarak kaydet
        temp_image_path = "temp_image." + image_file.name.split('.')[-1]
        with open(temp_image_path, "wb") as f:
            f.write(image_file.getbuffer())
        
        # ICC profili yüklendiyse yolunu al; yoksa None
        temp_icc_path = None
        if icc_file:
            temp_icc_path = "temp_icc.icc"
            with open(temp_icc_path, "wb") as f:
                f.write(icc_file.getbuffer())
        
        try:
            # ICC dönüşümünü uygula
            img_with_icc = apply_icc_profile(temp_image_path, temp_icc_path)
            
            if img_with_icc:
                # Aydınlatma koşulu uygulanıyor
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
        
        # Geçici dosyaları temizle
        try:
            os.remove(temp_image_path)
            if temp_icc_path:
                os.remove(temp_icc_path)
        except Exception:
            pass

if __name__ == "__main__":
    main()
